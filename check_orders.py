from sqlalchemy import select

from app.database import SessionLocal
from app.models.orders import Order


with SessionLocal() as db:
    orders = db.scalars(
        select(Order)
        .order_by(Order.created_at.desc())
        .limit(10)
    ).all()

    if not orders:
        print("Заявок в базе пока нет.")
    else:
        for order in orders:
            print("=" * 50)
            print(f"ID: {order.id}")
            print(f"Имя: {order.customer_name}")
            print(f"Телефон: {order.phone}")
            print(f"Дата: {order.requested_date}")
            print(f"Время: {order.requested_time}")
            print(f"Тип получения: {order.delivery_type}")
            print(f"Адрес доставки: {order.delivery_address}")
            print(f"Сумма: {order.total} ₽")
            print(f"Статус: {order.status}")
            print(f"Создана: {order.created_at}")

            print("Товары:")
            for item in order.items:
                print(
                    f"  - {item.product_name}: "
                    f"{item.price} ₽ × {item.quantity}"
                )

            if order.consent_event:
                print(
                    "Согласие:",
                    order.consent_event.consent_checked
                )