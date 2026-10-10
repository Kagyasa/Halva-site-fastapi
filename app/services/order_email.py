from html import escape

from app.services.common import format_money


def render_order_email(order, email_pickup_text, *, demo=False):
    order_id = order.id
    subtotal, delivery_fee, total = order.subtotal, order.delivery_fee, order.total
    email_items = [
        {
            "name": item.product_name,
            "price": item.price,
            "quantity": item.quantity,
            "line_total": item.price * item.quantity,
        }
        for item in order.items
    ]
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

    if order.delivery_type == "delivery":
        receiving_text = f"Доставка: {order.delivery_address}"
        receiving_html = f"<strong>Доставка:</strong> {escape(order.delivery_address or '')}"
    else:
        receiving_text = f"Самовывоз: {email_pickup_text}"
        receiving_html = f"<strong>Самовывоз:</strong> {escape(email_pickup_text or '')}"

    short_order_id = order_id[:8].upper()
    subject = f"Новая заявка Halva #{short_order_id} — {order.customer_name}"

    text_body = f"""Новая заявка с сайта Halva
Номер: #{short_order_id}

Клиент:
Имя: {order.customer_name}
Телефон: {order.phone}

Дата получения: {order.requested_date.strftime("%d.%m.%Y")}
Время: {order.requested_time.strftime("%H:%M")}

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
        <strong>Имя:</strong> {escape(order.customer_name)}<br>
        <strong>Телефон:</strong> {escape(order.phone)}
      </p>

      <p>
        <strong>Дата получения:</strong>
        {order.requested_date.strftime("%d.%m.%Y")}<br>
        <strong>Время:</strong>
        {order.requested_time.strftime("%H:%M")}
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

    if demo:
        subject = "[ДЕМО] " + subject
        text_body = "Демонстрационная заявка для проверки сайта.\n\n" + text_body
        html_body = (
            "<p><strong>Демонстрационная заявка для проверки сайта.</strong></p>" + html_body
        )
    return subject, text_body, html_body
