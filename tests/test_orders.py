import ssl
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import ConsentEvent, EmailNotification, Order, ShowcaseItem
from app.services.common import minimum_order_date
from app.services.notifications import deliver_one


def test_idempotency_money_snapshot_and_outbox(client, db_session, payload, catalog):
    first = client.post("/api/orders/", json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["total"] == "201.50"
    for _ in range(4):
        retry = client.post("/api/orders/", json=payload)
        assert retry.json() == first.json()
    assert db_session.scalar(select(func.count()).select_from(Order)) == 1
    assert db_session.scalar(select(func.count()).select_from(ConsentEvent)) == 1
    assert db_session.scalar(select(func.count()).select_from(EmailNotification)) == 1
    order = db_session.get(Order, first.json()["order_id"])
    assert order.phone == "+79227330330"
    assert order.total == Decimal("201.50")
    notification = db_session.scalar(select(EmailNotification))
    assert "&lt;b&gt;" in notification.html_body and "201.50 ₽" in notification.text_body
    # A later catalog edit cannot change the stored order or its email.
    catalog[0].price = Decimal("110.00")
    db_session.commit()
    assert client.post("/api/orders/", json=payload).json() == first.json()
    assert order.items[0].price == Decimal("100.75")


def test_idempotency_key_conflict(client, payload, db_session):
    assert client.post("/api/orders/", json=payload).status_code == 200
    payload["name"] = "Другой клиент"
    assert client.post("/api/orders/", json=payload).status_code == 409
    assert db_session.scalar(select(func.count()).select_from(Order)) == 1


def test_notification_failure_retry_and_restart(client, payload, db_session):
    assert client.post("/api/orders/", json=payload).status_code == 200
    with patch(
        "app.services.notifications._send_email_sync", side_effect=OSError("private SMTP response")
    ):
        assert deliver_one()
    db_session.expire_all()
    notification = db_session.scalar(select(EmailNotification))
    assert notification.status == "pending" and notification.attempts == 1
    assert notification.last_error == "OSError"
    notification.next_attempt_at -= timedelta(hours=1)
    db_session.commit()
    with patch("app.services.notifications._send_email_sync") as send:
        assert deliver_one()
        assert not deliver_one()
        assert send.call_count == 1
    db_session.expire_all()
    assert notification.status == "sent" and notification.attempts == 2


def test_certificate_failure_logs_reason_without_raw_smtp_response(client, payload, db_session):
    assert client.post("/api/orders/", json=payload).status_code == 200
    error = ssl.SSLCertVerificationError(1, "private SMTP response with credentials")
    error.verify_code = 20
    error.verify_message = "unable to get\nlocal issuer certificate"
    with (
        patch("app.services.notifications._send_email_sync", side_effect=error),
        patch("app.services.notifications.logger.warning") as warning,
    ):
        assert deliver_one()
    warning.assert_called_once()
    logged = warning.call_args.args[0] % warning.call_args.args[1:]
    assert "verify_code=20; unable to get local issuer certificate" in logged
    assert "private SMTP response" not in logged
    assert "credentials" not in logged
    db_session.expire_all()
    notification = db_session.scalar(select(EmailNotification))
    assert notification.status == "pending" and notification.attempts == 1
    assert notification.last_error == "SSLCertVerificationError"


@pytest.mark.parametrize(
    "change,status",
    [
        ({"consent": False}, 422),
        ({"phone": "12345678901"}, 422),
        ({"pickup_location_id": "улица"}, 400),
        ({"time": "12:00:00+03:00"}, 422),
        ({"expected_total": "201.00"}, 409),
        ({"website": "spam"}, 400),
        ({"privacy_policy_version_id": "old-version"}, 409),
    ],
)
def test_rejected_orders_do_not_persist(client, db_session, payload, change, status):
    payload.update(change)
    result = client.post("/api/orders/", json=payload)
    assert result.status_code == status, result.text
    assert db_session.scalar(select(func.count()).select_from(Order)) == 0
    assert db_session.scalar(select(func.count()).select_from(EmailNotification)) == 0


def test_inactive_category_is_hidden_everywhere(client, db_session, catalog, payload):
    product, location = catalog
    db_session.add(ShowcaseItem(product=product, pickup_location=location))
    product.category.is_active = False
    db_session.commit()
    assert client.get("/api/products/").json() == []
    assert client.get("/api/products/available/").json() == []
    assert client.get("/api/showcase/").json() == []
    assert client.post("/api/orders/", json=payload).status_code == 400


def test_delivery_fee_and_server_date(client, payload):
    payload.update(
        delivery_type="delivery",
        pickup_location_id=None,
        address="Тестовая улица 1",
        expected_total="351.50",
    )
    assert client.post("/api/orders/", json=payload).json()["total"] == "351.50"
    config = client.get("/api/checkout/").json()
    assert config["minimum_date"] == str(minimum_order_date())
    assert config["delivery_price"] == "150.00"


def test_invalid_product_price_rejected_by_database(db_session, catalog):
    catalog[0].price = Decimal("-0.01")
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_fractional_and_duplicate_quantities_rejected(client, payload):
    payload["items"][0]["quantity"] = 1.5
    assert client.post("/api/orders/", json=payload).status_code == 422
    payload["items"][0]["quantity"] = 1
    payload["items"].append(payload["items"][0].copy())
    assert client.post("/api/orders/", json=payload).status_code == 422
