import asyncio
import smtplib
import ssl
from email.message import EmailMessage

import certifi

from app.config import get_settings


def _send_email_sync(
    subject: str, text_body: str, html_body: str, message_id: str | None = None
) -> None:
    settings = get_settings()
    settings.validate_smtp()
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.email_from or settings.smtp_username
    message["To"] = settings.orders_email
    if message_id:
        message["Message-ID"] = message_id
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")
    context = ssl.create_default_context()
    # Keep the system trust store and supplement it with Mozilla's CA bundle.
    # Hostname and certificate verification remain enabled for both transports.
    context.load_verify_locations(cafile=certifi.where())
    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(
            settings.smtp_host, settings.smtp_port, timeout=20, context=context
        ) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)


async def send_email(subject: str, text_body: str, html_body: str) -> None:
    await asyncio.to_thread(_send_email_sync, subject, text_body, html_body)
