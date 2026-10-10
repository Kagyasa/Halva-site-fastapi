from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.cli import publish_document
from app.config import Settings
from app.database import Base
from app.models import ConsentTextVersion, PrivacyPolicyVersion
from app.services import email, rate_limit
from app.services.common import utc_now
from app.services.legal import LEGACY_CONSENT, sha256_text


def test_placeholder_legal_documents_are_unavailable(client, db_session, catalog):
    policy = PrivacyPolicyVersion(
        version="1.0",
        title="Политика",
        text="Здесь будет полный текст Политики обработки персональных данных.",
        is_active=True,
        published_at=utc_now(),
    )
    consent = ConsentTextVersion(
        version="1.0", text=LEGACY_CONSENT, is_active=True, published_at=utc_now()
    )
    policy.content_sha256, consent.content_sha256 = (
        sha256_text(policy.text),
        sha256_text(consent.text),
    )
    db_session.add_all([policy, consent])
    db_session.commit()
    config = client.get("/api/checkout/").json()
    assert config["available"] is False and config["privacy_policy"] is None
    assert client.get("/api/legal/privacy-policy/").status_code == 404
    with pytest.raises(ValueError):
        publish_document(
            db_session, PrivacyPolicyVersion, version="2.0", text=policy.text, title="Политика"
        )


def test_public_and_accepted_versions_use_publication_time(client, db_session, payload, legal):
    old_policy, _ = legal
    newer = PrivacyPolicyVersion(
        version="newer",
        title="Только тест",
        text="Новая синтетическая политика для автоматических тестов приложения.",
        is_active=True,
        published_at=utc_now() + timedelta(hours=1),
        created_at=utc_now() - timedelta(days=1),
    )
    newer.content_sha256 = sha256_text(newer.text)
    db_session.add(newer)
    db_session.commit()
    assert client.get("/api/legal/privacy-policy/").json()["id"] == newer.id
    assert client.get("/api/checkout/").json()["privacy_policy"]["id"] == newer.id
    response = client.post("/api/orders/", json=payload)
    assert response.status_code == 409 and response.headers["X-Legal-Changed"] == "true"
    payload["privacy_policy_version_id"] = newer.id
    assert client.post("/api/orders/", json=payload).status_code == 200


def test_published_versions_are_immutable(db_session, legal):
    policy, _ = legal
    with pytest.raises(ValueError):
        publish_document(
            db_session,
            PrivacyPolicyVersion,
            version=policy.version,
            title=policy.title,
            text="Другой синтетический текст для проверки неизменности версии.",
        )
    db_session.rollback()
    old_id = policy.id
    publish_document(
        db_session,
        PrivacyPolicyVersion,
        version="next",
        title="Только тест",
        text="Следующая синтетическая политика для автоматических тестов.",
    )
    db_session.commit()
    db_session.refresh(policy)
    assert policy.id == old_id and policy.is_active is False


@pytest.mark.parametrize("use_ssl", [True, False])
def test_smtp_validates_certificates(monkeypatch, use_ssl):
    settings = Settings(
        _env_file=None,
        smtp_host="smtp.test.invalid",
        smtp_username="test",
        smtp_password="test",
        orders_email="test@example.invalid",
        smtp_use_ssl=use_ssl,
        smtp_starttls=not use_ssl,
    )
    monkeypatch.setattr(email, "get_settings", lambda: settings)
    transport = MagicMock()
    smtp = transport.return_value.__enter__.return_value
    monkeypatch.setattr(email.smtplib, "SMTP_SSL" if use_ssl else "SMTP", transport)
    email._send_email_sync("Тест", "Только тест", "<p>Только тест</p>")
    context = (
        transport.call_args.kwargs["context"]
        if use_ssl
        else smtp.starttls.call_args.kwargs["context"]
    )
    assert context.check_hostname is True
    import ssl

    assert context.verify_mode == ssl.CERT_REQUIRED
    smtp.send_message.assert_called_once()


def test_limiter_removes_expired_ip_buckets(monkeypatch):
    clock = [0.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: clock[0])
    limiter = rate_limit.FailedLoginRateLimiter(max_failures=3)
    for index in range(300):
        limiter.record_failure(f"ip-{index}")
    clock[0] += 1000
    for _ in range(100):
        limiter.is_blocked("active")
    assert not limiter._failures


def test_migrations_match_models(db_session):
    context = MigrationContext.configure(db_session.connection())
    assert compare_metadata(context, Base.metadata) == []
