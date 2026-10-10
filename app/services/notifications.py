"""Retry durable notifications. PostgreSQL row locks prevent competing claims."""

import logging
import ssl
from datetime import timedelta
from threading import Event

from sqlalchemy import and_, or_, select, update

from app.database import SessionLocal
from app.models.notifications import EmailNotification
from app.services.common import generate_uuid, utc_now
from app.services.email import _send_email_sync

logger = logging.getLogger(__name__)


def deliver_one() -> bool:
    now, token = utc_now(), generate_uuid()
    with SessionLocal() as db:
        notification = db.scalar(
            select(EmailNotification)
            .where(
                or_(
                    and_(
                        EmailNotification.status == "pending",
                        EmailNotification.next_attempt_at <= now,
                    ),
                    and_(
                        EmailNotification.status == "sending", EmailNotification.leased_until <= now
                    ),
                )
            )
            .order_by(EmailNotification.next_attempt_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if notification is None:
            return False
        notification.status = "sending"
        notification.leased_until = now + timedelta(minutes=10)
        notification.lease_token = token
        notification.attempts += 1
        notification_id, attempts = notification.id, notification.attempts
        subject, text_body, html_body = (
            notification.subject,
            notification.text_body,
            notification.html_body,
        )
        db.commit()

    error = None
    try:
        _send_email_sync(
            subject, text_body, html_body, f"<halva-order-{notification_id}@halva.local>"
        )
    except Exception as exc:
        # Keep only the exception type in the database. TLS verification details
        # are safe to log separately; never log the raw SMTP exception.
        error = type(exc).__name__
        if isinstance(exc, ssl.SSLCertVerificationError):
            reason = " ".join(
                str(getattr(exc, "verify_message", "Certificate verification failed")).split()
            )[:300]
            logger.warning(
                "Notification %s failed (%s; verify_code=%s; %s); will retry",
                notification_id,
                error,
                getattr(exc, "verify_code", None),
                reason,
            )
        else:
            logger.warning("Notification %s failed (%s); will retry", notification_id, error)

    with SessionLocal() as db:
        values = {"lease_token": None, "leased_until": None, "last_error": error}
        if error:
            values.update(
                status="pending",
                next_attempt_at=utc_now()
                + timedelta(seconds=min(3600, 30 * 2 ** min(attempts - 1, 7))),
            )
        else:
            values.update(status="sent", sent_at=utc_now())
        db.execute(
            update(EmailNotification)
            .where(
                EmailNotification.id == notification_id,
                EmailNotification.lease_token == token,
            )
            .values(**values)
        )
        db.commit()
    return True


def run_worker(stop: Event | None = None) -> None:
    stop = stop or Event()
    while not stop.is_set():
        try:
            if deliver_one():
                continue
        except Exception as exc:
            logger.warning("Notification worker unavailable (%s)", type(exc).__name__)
        stop.wait(5)
