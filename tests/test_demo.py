import uuid
from unittest.mock import patch

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from starlette.testclient import TestClient

import app.main as main_module
from app.cli import publish_document
from app.config import Settings, get_settings
from app.models import (
    ConsentEvent,
    ConsentTextVersion,
    EmailNotification,
    Order,
    PrivacyPolicyVersion,
)
from app.services.legal import DEMO_ORDER_NOTE, DEMO_VERSION_PREFIX, active_documents
from app.services.notifications import deliver_one


@pytest.fixture
def demo_client(db_session, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    get_settings.cache_clear()
    monkeypatch.setattr(main_module, "settings", get_settings())
    try:
        with TestClient(main_module.create_app()) as client:
            yield client
    finally:
        get_settings.cache_clear()


def use_demo_versions(client, payload):
    checkout = client.get("/api/checkout/").json()
    assert checkout["available"] and checkout["demo_mode"]
    payload["privacy_policy_version_id"] = checkout["privacy_policy"]["id"]
    payload["consent_text_version_id"] = checkout["consent_text"]["id"]
    return checkout


def test_demo_accepts_orders_without_final_legal_documents(demo_client, db_session, catalog):
    product, location = catalog
    checkout = demo_client.get("/api/checkout/").json()
    assert checkout["available"] and checkout["demo_mode"]
    result = demo_client.post(
        "/api/orders/",
        json={
            "name": "Демонстрационный клиент",
            "phone": "+70000000000",
            "date": checkout["minimum_date"],
            "time": "12:00",
            "items": [{"product_id": product.id, "quantity": 1}],
            "delivery_type": "pickup",
            "pickup_location_id": location.id,
            "consent": True,
            "privacy_policy_version_id": checkout["privacy_policy"]["id"],
            "consent_text_version_id": checkout["consent_text"]["id"],
            "expected_total": "100.75",
            "idempotency_key": uuid.uuid4().hex,
        },
    )
    assert result.status_code == 200, result.text
    assert db_session.scalar(select(func.count()).select_from(Order)) == 1


def test_demo_startup_prepares_documents_without_replacing_real_versions(
    demo_client, db_session, payload, legal
):
    checkout = use_demo_versions(demo_client, payload)
    assert checkout["privacy_policy"]["version"].startswith(DEMO_VERSION_PREFIX)
    assert "ДЕМОНСТРАЦИОННЫЙ" in checkout["privacy_policy"]["text"]
    assert (
        demo_client.get("/api/legal/privacy-policy/").json()["id"]
        == checkout["privacy_policy"]["id"]
    )
    assert demo_client.get("/api/legal/consent/").json()["id"] == checkout["consent_text"]["id"]
    for document in legal:
        db_session.refresh(document)
        assert document.is_active
    assert db_session.scalar(select(func.count()).select_from(PrivacyPolicyVersion)) == 2
    assert db_session.scalar(select(func.count()).select_from(ConsentTextVersion)) == 2
    with TestClient(main_module.create_app()):
        pass
    assert db_session.scalar(select(func.count()).select_from(PrivacyPolicyVersion)) == 2


def test_demo_order_is_saved_and_email_is_delivered(demo_client, db_session, payload):
    checkout = use_demo_versions(demo_client, payload)
    result = demo_client.post("/api/orders/", json=payload)
    assert result.status_code == 200, result.text
    retry = demo_client.post("/api/orders/", json=payload)
    assert retry.json()["order_id"] == result.json()["order_id"]
    order = db_session.scalar(select(Order))
    assert order.staff_notes == DEMO_ORDER_NOTE
    evidence = db_session.scalar(select(ConsentEvent))
    assert evidence.privacy_policy_version_id == checkout["privacy_policy"]["id"]
    notification = db_session.scalar(select(EmailNotification))
    assert notification.subject.startswith("[ДЕМО]")
    assert "Демонстрационная заявка" in notification.text_body
    with patch("app.services.notifications._send_email_sync") as send:
        assert deliver_one()
        assert send.call_count == 1
    db_session.refresh(notification)
    assert notification.status == "sent"
    assert db_session.scalar(select(func.count()).select_from(Order)) == 1


def test_demo_allows_repeated_presentation_orders(demo_client, db_session, payload):
    use_demo_versions(demo_client, payload)
    for _ in range(7):
        payload["idempotency_key"] = uuid.uuid4().hex
        result = demo_client.post("/api/orders/", json=payload)
        assert result.status_code == 200, result.text
    assert db_session.scalar(select(func.count()).select_from(Order)) == 7


def test_demo_still_requires_consent_and_correct_price(demo_client, payload):
    use_demo_versions(demo_client, payload)
    payload["consent"] = False
    assert demo_client.post("/api/orders/", json=payload).status_code == 422
    payload["consent"] = True
    payload["expected_total"] = "0.00"
    assert demo_client.post("/api/orders/", json=payload).status_code == 409


def test_disabling_demo_hides_demo_documents_without_deleting_orders(
    demo_client, db_session, payload, legal, monkeypatch
):
    use_demo_versions(demo_client, payload)
    assert demo_client.post("/api/orders/", json=payload).status_code == 200
    monkeypatch.setenv("DEMO_MODE", "false")
    get_settings.cache_clear()
    policy, consent = active_documents(db_session)
    assert (policy.id, consent.id) == (legal[0].id, legal[1].id)
    # With no final documents, switching off the demo closes new order submission.
    for document in legal:
        document.is_active = False
    db_session.commit()
    checkout = demo_client.get("/api/checkout/").json()
    assert checkout["available"] is False and checkout["demo_mode"] is False
    assert demo_client.get("/api/legal/privacy-policy/").status_code == 404
    payload["idempotency_key"] = uuid.uuid4().hex
    assert demo_client.post("/api/orders/", json=payload).status_code == 503
    assert db_session.scalar(select(func.count()).select_from(Order)) == 1


def test_demo_cannot_be_enabled_as_production():
    with pytest.raises(ValidationError, match="DEMO_MODE"):
        Settings(_env_file=None, app_env="production", demo_mode=True)


def test_demo_versions_cannot_be_published_as_final_documents(db_session):
    with pytest.raises(ValueError, match="зарезервирован"):
        publish_document(
            db_session,
            PrivacyPolicyVersion,
            version=DEMO_VERSION_PREFIX + "policy-1",
            text="Текст для автоматического теста публикации готовой версии документа.",
            title="Только тест",
        )
