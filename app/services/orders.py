"""Order validation and one atomic write of the order, consent and notification."""

import hashlib
import hmac
import json
import logging
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.catalog import Category, PickupLocation, Product
from app.models.notifications import EmailNotification
from app.models.orders import ConsentEvent, Order, OrderItem
from app.schemas.orders import OrderCreateRequest, OrderCreateResponse
from app.services.common import generate_uuid, minimum_order_date
from app.services.legal import DEMO_ORDER_NOTE, active_documents
from app.services.order_email import render_order_email
from app.services.rate_limit import OrderRateLimiter, order_rate_limiter

logger = logging.getLogger(__name__)
ACCEPTED_MESSAGE = "Заявка принята! Мы свяжемся с вами для подтверждения."
demo_order_rate_limiter = OrderRateLimiter(short_max_requests=100, daily_max_requests=1000)


def order_response(order: Order) -> OrderCreateResponse:
    return OrderCreateResponse(
        success=True, message=ACCEPTED_MESSAGE, total=order.total, order_id=order.id
    )


def request_fingerprint(data: OrderCreateRequest) -> str:
    payload = data.model_dump(mode="json", exclude={"idempotency_key", "website"})
    payload["items"] = sorted(payload["items"], key=lambda item: item["product_id"])
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def existing_order(db: Session, key: str, fingerprint: str):
    order = db.scalar(select(Order).where(Order.idempotency_key == key))
    if order and not hmac.compare_digest(order.request_sha256 or "", fingerprint):
        raise HTTPException(
            409, "Эта попытка отправки уже содержит другие данные. Отправьте заявку заново."
        )
    return order


def save_order(db: Session, data: OrderCreateRequest, *, client_ip: str, user_agent: str):
    if data.website.strip():
        raise HTTPException(400, "Некорректные данные формы.")
    fingerprint = request_fingerprint(data)
    saved = existing_order(db, data.idempotency_key, fingerprint)
    if saved:
        return order_response(saved)
    if data.date < minimum_order_date():
        raise HTTPException(422, "Дата получения должна быть не раньше завтрашнего дня")

    policy, consent = active_documents(db)
    if policy is None or consent is None:
        raise HTTPException(
            503, "Приём заявок станет доступен после публикации политики и согласия."
        )
    if data.privacy_policy_version_id != policy.id or data.consent_text_version_id != consent.id:
        raise HTTPException(
            409,
            "Документы обновились. Ознакомьтесь с ними и подтвердите согласие ещё раз.",
            headers={"X-Legal-Changed": "true"},
        )

    quantities = {item.product_id: item.quantity for item in data.items}
    products = db.scalars(
        select(Product)
        .join(Product.category)
        .where(
            Product.id.in_(quantities),
            Product.is_active.is_(True),
            Product.is_available_for_order.is_(True),
            Category.is_active.is_(True),
        )
    ).all()
    if len(products) != len(quantities):
        raise HTTPException(400, "Один или несколько выбранных товаров недоступны для заказа.")
    if any(product.price < 0 for product in products):
        raise HTTPException(
            503, "В каталоге обнаружена некорректная цена. Свяжитесь с кондитерской."
        )

    location = None
    if data.delivery_type == "pickup":
        location = db.scalar(
            select(PickupLocation).where(
                PickupLocation.id == data.pickup_location_id,
                PickupLocation.is_active.is_(True),
            )
        )
        if location is None:
            raise HTTPException(400, "Выбранная точка самовывоза недоступна.")

    subtotal = sum(
        (product.price * quantities[product.id] for product in products), Decimal("0.00")
    )
    delivery_fee = (
        get_settings().delivery_price if data.delivery_type == "delivery" else Decimal("0.00")
    )
    total = subtotal + delivery_fee
    if total > Decimal("99999999.99"):
        raise HTTPException(422, "Сумма заявки превышает допустимое значение")

    if data.expected_total != total:
        raise HTTPException(
            409,
            "Цены обновились. Проверьте новую сумму и отправьте заявку ещё раз.",
            headers={"X-Catalog-Changed": "true"},
        )

    limiter = demo_order_rate_limiter if get_settings().demo_mode else order_rate_limiter
    allowed, retry_after = limiter.check(client_ip)
    if not allowed:
        raise HTTPException(
            429,
            "Слишком много заявок. Попробуйте позже.",
            headers={"Retry-After": str(retry_after)},
        )

    order = Order(
        id=generate_uuid(),
        idempotency_key=data.idempotency_key,
        request_sha256=fingerprint,
        customer_name=data.name,
        phone=data.phone,
        requested_date=data.date,
        requested_time=data.time,
        delivery_type=data.delivery_type,
        pickup_location_id=location.id if location else None,
        delivery_address=data.address if data.delivery_type == "delivery" else None,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=total,
        status="new",
        staff_notes=DEMO_ORDER_NOTE if get_settings().demo_mode else None,
    )
    order.items = [
        OrderItem(
            product_id=product.id,
            product_name=product.name,
            price=product.price,
            quantity=quantities[product.id],
        )
        for product in products
    ]
    evidence = "|".join(
        (
            order.id,
            policy.content_sha256,
            consent.content_sha256,
            client_ip,
            user_agent,
            data.idempotency_key,
        )
    )
    order.consent_event = ConsentEvent(
        privacy_policy_version_id=policy.id,
        consent_text_version_id=consent.id,
        consent_checked=True,
        ip_address=client_ip if client_ip != "unknown" else None,
        user_agent=user_agent,
        request_id=data.idempotency_key,
        policy_sha256=policy.content_sha256,
        consent_sha256=consent.content_sha256,
        evidence_signature=hashlib.sha256(evidence.encode()).hexdigest(),
    )
    subject, text_body, html_body = render_order_email(
        order, location.address if location else None, demo=get_settings().demo_mode
    )
    db.add(order)
    db.add(
        EmailNotification(order=order, subject=subject, text_body=text_body, html_body=html_body)
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        saved = existing_order(db, data.idempotency_key, fingerprint)
        if saved:
            return order_response(saved)
        logger.error("Order transaction violated a database constraint")
        raise HTTPException(503, "Не удалось сохранить заявку. Попробуйте ещё раз.") from None
    except SQLAlchemyError:
        db.rollback()
        logger.error("Order transaction could not be committed")
        raise HTTPException(503, "Не удалось сохранить заявку. Попробуйте ещё раз.") from None
    return order_response(order)
