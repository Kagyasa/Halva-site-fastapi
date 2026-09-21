import hashlib
import logging
import uuid
from decimal import Decimal
from html import escape

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.database import SessionLocal
from app.models.catalog import PickupLocation, Product
from app.models.orders import (
    ConsentEvent,
    ConsentTextVersion,
    Order,
    OrderItem,
    PrivacyPolicyVersion,
)
from app.schemas.orders import OrderEmailRequest, OrderEmailResponse
from app.services.email import send_email


router = APIRouter(
    prefix="/api/orders",
    tags=["orders"],
)

logger = logging.getLogger(__name__)

DELIVERY_PRICE = Decimal("150.00")


def format_money(value: Decimal) -> str:
    return f"{int(value)} ₽"


def normalize_location(value: str) -> str:
    return (
        value.casefold()
        .replace("ё", "е")
        .replace("г.", "")
        .replace("ул.", "")
        .replace("улица", "")
        .replace(" ", "")
        .replace(".", "")
        .replace(",", "")
    )


def find_pickup_location(
    db,
    value: str | None,
) -> PickupLocation | None:
    if not value:
        return None

    locations = db.scalars(
        select(PickupLocation).where(PickupLocation.is_active.is_(True))
    ).all()

    for location in locations:
        if location.id == value:
            return location

    requested = normalize_location(value)

    for location in locations:
        for candidate in (location.name or "", location.address or ""):
            normalized = normalize_location(candidate)
            if (
                requested == normalized
                or requested in normalized
                or normalized in requested
            ):
                return location

    return None


def make_evidence_signature(
    *,
    order_id: str,
    policy_sha256: str,
    consent_sha256: str,
    ip_address: str | None,
    user_agent: str | None,
    request_id: str,
) -> str:
    evidence = "|".join(
        [
            order_id,
            policy_sha256,
            consent_sha256,
            ip_address or "",
            user_agent or "",
            request_id,
        ]
    )
    return hashlib.sha256(evidence.encode("utf-8")).hexdigest()


@router.post("/", response_model=OrderEmailResponse)
async def create_order(
    order_data: OrderEmailRequest,
    request: Request,
) -> OrderEmailResponse:
    order_id = uuid.uuid4().hex
    request_id = uuid.uuid4().hex

    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    quantities_by_product_id = {
        item.product_id: item.quantity
        for item in order_data.items
    }
    product_ids = list(quantities_by_product_id)

    email_items: list[dict[str, object]] = []
    email_pickup_text: str | None = None

    with SessionLocal() as db:
        # Берём товары и реальные цены только из БД.
        products = db.scalars(
            select(Product).where(
                Product.id.in_(product_ids),
                Product.is_active.is_(True),
                Product.is_available_for_order.is_(True),
            )
        ).all()

        products_by_id = {
            product.id: product
            for product in products
        }

        if len(products_by_id) != len(product_ids):
            raise HTTPException(
                status_code=400,
                detail="Один или несколько выбранных товаров недоступны для заказа.",
            )

        ordered_products = [
            products_by_id[product_id]
            for product_id in product_ids
        ]

        privacy_policy = db.scalar(
            select(PrivacyPolicyVersion)
            .where(PrivacyPolicyVersion.is_active.is_(True))
            .order_by(PrivacyPolicyVersion.created_at.desc())
            .limit(1)
        )

        consent_text = db.scalar(
            select(ConsentTextVersion)
            .where(ConsentTextVersion.is_active.is_(True))
            .order_by(ConsentTextVersion.created_at.desc())
            .limit(1)
        )

        if privacy_policy is None or consent_text is None:
            raise HTTPException(
                status_code=503,
                detail="Документы согласия временно недоступны. Попробуйте ещё раз позже.",
            )

        pickup_location = None

        if order_data.delivery_type == "pickup":
            pickup_location = find_pickup_location(
                db,
                order_data.pickup_location,
            )

            if pickup_location is None:
                raise HTTPException(
                    status_code=400,
                    detail="Не удалось определить выбранную точку самовывоза.",
                )

            email_pickup_text = (
                pickup_location.address or pickup_location.name
            )

        # Сумма считается с учётом количества каждого товара.
        subtotal = sum(
            (
                Decimal(str(product.price))
                * quantities_by_product_id[product.id]
                for product in ordered_products
            ),
            start=Decimal("0.00"),
        )

        delivery_fee = (
            DELIVERY_PRICE
            if order_data.delivery_type == "delivery"
            else Decimal("0.00")
        )

        total = subtotal + delivery_fee

        # В заявке, БД и email используем ПОЛНОЕ имя Product.name.
        email_items = [
            {
                "name": product.name,
                "price": Decimal(str(product.price)),
                "quantity": quantities_by_product_id[product.id],
                "line_total": (
                    Decimal(str(product.price))
                    * quantities_by_product_id[product.id]
                ),
            }
            for product in ordered_products
        ]

        db_order = Order(
            id=order_id,
            customer_name=order_data.name,
            phone=order_data.phone,
            requested_date=order_data.date,
            requested_time=order_data.time,
            delivery_type=order_data.delivery_type,
            pickup_location_id=(
                pickup_location.id if pickup_location else None
            ),
            delivery_address=(
                order_data.address
                if order_data.delivery_type == "delivery"
                else None
            ),
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=total,
            status="new",
        )

        for product in ordered_products:
            quantity = quantities_by_product_id[product.id]

            db_order.items.append(
                OrderItem(
                    product_id=product.id,
                    product_name=product.name,
                    price=Decimal(str(product.price)),
                    quantity=quantity,
                )
            )

        evidence_signature = make_evidence_signature(
            order_id=order_id,
            policy_sha256=privacy_policy.content_sha256,
            consent_sha256=consent_text.content_sha256,
            ip_address=client_ip,
            user_agent=user_agent,
            request_id=request_id,
        )

        db_order.consent_event = ConsentEvent(
            privacy_policy_version_id=privacy_policy.id,
            consent_text_version_id=consent_text.id,
            consent_checked=order_data.consent,
            ip_address=client_ip,
            user_agent=user_agent,
            request_id=request_id,
            policy_sha256=privacy_policy.content_sha256,
            consent_sha256=consent_text.content_sha256,
            evidence_signature=evidence_signature,
        )

        db.add(db_order)

        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Не удалось сохранить заказ %s", order_id)
            raise HTTPException(
                status_code=500,
                detail="Не удалось сохранить заявку. Попробуйте ещё раз.",
            )

    product_lines_text = "\n".join(
        (
            f"• {item['name']} — "
            f"{format_money(item['price'])} × {item['quantity']} = "
            f"{format_money(item['line_total'])}"
        )
        for item in email_items
    )

    product_lines_html = "".join(
        (
            "<li>"
            f"{escape(str(item['name']))} — "
            f"{escape(format_money(item['price']))} × "
            f"{item['quantity']} = "
            f"<strong>{escape(format_money(item['line_total']))}</strong>"
            "</li>"
        )
        for item in email_items
    )

    if order_data.delivery_type == "delivery":
        receiving_text = f"Доставка: {order_data.address}"
        receiving_html = (
            f"<strong>Доставка:</strong> "
            f"{escape(order_data.address or '')}"
        )
    else:
        receiving_text = f"Самовывоз: {email_pickup_text}"
        receiving_html = (
            f"<strong>Самовывоз:</strong> "
            f"{escape(email_pickup_text or '')}"
        )

    short_order_id = order_id[:8].upper()
    subject = (
        f"Новая заявка Halva #{short_order_id} — {order_data.name}"
    )

    text_body = f"""Новая заявка с сайта Halva
Номер: #{short_order_id}

Клиент:
Имя: {order_data.name}
Телефон: {order_data.phone}

Дата получения: {order_data.date.strftime("%d.%m.%Y")}
Время: {order_data.time.strftime("%H:%M")}

Заказ:
{product_lines_text}

{receiving_text}

Подытог: {format_money(subtotal)}
Доставка: {format_money(delivery_fee)}
Итого: {format_money(total)}
"""

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#1a1a1a;">
      <h2 style="margin-bottom:8px;">Новая заявка с сайта Halva</h2>
      <p style="margin-top:0;color:#666;">
        Номер: #{escape(short_order_id)}
      </p>

      <p>
        <strong>Имя:</strong> {escape(order_data.name)}<br>
        <strong>Телефон:</strong> {escape(order_data.phone)}
      </p>

      <p>
        <strong>Дата получения:</strong>
        {order_data.date.strftime("%d.%m.%Y")}<br>
        <strong>Время:</strong>
        {order_data.time.strftime("%H:%M")}
      </p>

      <p><strong>Заказ:</strong></p>
      <ul>{product_lines_html}</ul>

      <p>{receiving_html}</p>

      <p>
        <strong>Подытог:</strong>
        {escape(format_money(subtotal))}<br>
        <strong>Доставка:</strong>
        {escape(format_money(delivery_fee))}<br>
        <strong>Итого:</strong>
        {escape(format_money(total))}
      </p>
    </div>
    """

    try:
        await send_email(
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )

        message = (
            "Заявка отправлена! "
            "Мы свяжемся с вами для подтверждения."
        )

    except Exception:
        logger.exception(
            "Заказ %s сохранён, но email-уведомление не отправлено",
            order_id,
        )

        message = (
            "Заявка принята! "
            "Мы свяжемся с вами для подтверждения."
        )

    return OrderEmailResponse(
        success=True,
        message=message,
        total=int(total),
    )
