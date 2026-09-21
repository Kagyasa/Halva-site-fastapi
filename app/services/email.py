import asyncio
import smtplib
from email.message import EmailMessage

from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailSettings(BaseSettings):
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str

    smtp_use_ssl: bool = False
    smtp_starttls: bool = True

    email_from: str | None = None
    orders_email: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


def _send_email_sync(subject: str, text_body: str, html_body: str) -> None:
    settings = EmailSettings()

    sender = settings.email_from or settings.smtp_username

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = settings.orders_email
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=20,
        ) as smtp:
            smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
        timeout=20,
    ) as smtp:
        smtp.ehlo()

        if settings.smtp_starttls:
            smtp.starttls()
            smtp.ehlo()

        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


async def send_email(subject: str, text_body: str, html_body: str) -> None:
    await asyncio.to_thread(
        _send_email_sync,
        subject,
        text_body,
        html_body,
    )
