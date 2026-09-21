from decimal import Decimal
from html import escape

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database import SessionLocal
from app.models.catalog import Product
from app.schemas.orders import OrderEmailRequest, OrderEmailResponse
from app.services.email import send_email


router = APIRouter(
    prefix="/api/orders",
    tags=["orders"],
)

DELIVERY_PRICE = Decimal("150")


def format_money(value: Decimal) -> str:
    return f"{int(value)} ₽"


@router.post("/", response_model=OrderEmailResponse)
async def create_order(order: OrderEmailRequest) -> OrderEmailResponse:
    with SessionLocal() as db:
        products = db.scalars(
            select(Product).where(
                Product.id.in_(order.product_ids),
                Product.is_active.is_(True),
                Product.is_available_for_order.is_(True),
            )
        ).all()

    products_by_id = {product.id: product for product in products}
    ordered_products = [
        products_by_id[product_id]
        for product_id in order.product_ids
        if product_id in products_by_id
    ]

    if len(ordered_products) != len(set(order.product_ids)):
        raise HTTPException(
            status_code=400,
            detail="Один или несколько выбранных товаров недоступны для заказа.",
        )

    products_total = sum(
        (Decimal(str(product.price)) for product in ordered_products),
        start=Decimal("0"),
    )

    delivery_price = (
        DELIVERY_PRICE if order.delivery_type == "delivery" else Decimal("0")
    )
    total = products_total + delivery_price

    product_lines_text = "\n".join(
        f"• {product.display_name or product.name} — {format_money(Decimal(str(product.price)))}"
        for product in ordered_products
    )

    product_lines_html = "".join(
        "<li>"
        f"{escape(product.display_name or product.name)} — "
        f"<strong>{escape(format_money(Decimal(str(product.price))))}</strong>"
        "</li>"
        for product in ordered_products
    )

    if order.delivery_type == "delivery":
        receiving_text = f"Доставка: {order.address}"
        receiving_html = f"<strong>Доставка:</strong> {escape(order.address or '')}"
    else:
        receiving_text = f"Самовывоз: {order.pickup_location}"
        receiving_html = f"<strong>Самовывоз:</strong> {escape(order.pickup_location or '')}"

    subject = f"Новая заявка с сайта Halva — {order.name}"

    text_body = f"""Новая заявка с сайта Halva

Клиент:
Имя: {order.name}
Телефон: {order.phone}

Дата получения: {order.date.strftime("%d.%m.%Y")}
Время: {order.time.strftime("%H:%M")}

Заказ:
{product_lines_text}

{receiving_text}

Доставка: {format_money(delivery_price)}
Итого: {format_money(total)}
"""

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:640px;margin:auto;color:#1a1a1a;">
      <h2 style="margin-bottom:20px;">Новая заявка с сайта Halva</h2>

      <p>
        <strong>Имя:</strong> {escape(order.name)}<br>
        <strong>Телефон:</strong> {escape(order.phone)}
      </p>

      <p>
        <strong>Дата получения:</strong> {order.date.strftime("%d.%m.%Y")}<br>
        <strong>Время:</strong> {order.time.strftime("%H:%M")}
      </p>

      <p><strong>Заказ:</strong></p>
      <ul>{product_lines_html}</ul>

      <p>{receiving_html}</p>

      <p>
        <strong>Доставка:</strong> {escape(format_money(delivery_price))}<br>
        <strong>Итого:</strong> {escape(format_money(total))}
      </p>
    </div>
    """

    try:
        await send_email(
            subject=subject,
            text_body=text_body,
            html_body=html_body,
        )
    except Exception as exc:
        print("\n========== EMAIL ERROR ==========")
        print(type(exc).__name__)
        print(str(exc))
        print("=================================\n")

        raise HTTPException(
            status_code=503,
            detail="Заявка заполнена, но письмо сейчас не удалось отправить. Попробуйте ещё раз чуть позже.",
        ) from exc

    return OrderEmailResponse(
        success=True,
        message="Заявка отправлена! Мы свяжемся с вами для подтверждения.",
        total=int(total),
    )
