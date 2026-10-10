import os
import uuid
from decimal import Decimal

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

from alembic import command

# Tests never use a developer's .env database or real SMTP service.
os.environ.update(
    APP_ENV="test", DATABASE_URL="sqlite://", EMAIL_WORKER_ENABLED="false", DEMO_MODE="false"
)

import app.admin as admin_module
import app.admin_security as security_module
import app.cli as cli_module
import app.database as database_module
from app.admin_security import password_hasher
from app.main import create_app
from app.models import (
    AdminUser,
    Category,
    ConsentTextVersion,
    PickupLocation,
    PrivacyPolicyVersion,
    Product,
)
from app.services import notifications, orders, rate_limit
from app.services.common import minimum_order_date, utc_now
from app.services.legal import sha256_text


@pytest.fixture
def db_session(tmp_path, monkeypatch):
    schema = "halva_test_" + uuid.uuid4().hex
    url = os.environ.get("TEST_DATABASE_URL")
    root_engine = None
    if url:
        root_engine = create_engine(url)
        with root_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(
            f"sqlite:///{tmp_path / 'test.sqlite'}", connect_args={"check_same_thread": False}
        )
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(admin_module, "engine", engine)
    for module in (database_module, admin_module, security_module, cli_module, notifications):
        monkeypatch.setattr(module, "SessionLocal", factory)
    monkeypatch.setattr(orders, "order_rate_limiter", rate_limit.OrderRateLimiter())
    monkeypatch.setattr(
        orders,
        "demo_order_rate_limiter",
        rate_limit.OrderRateLimiter(short_max_requests=100, daily_max_requests=1000),
    )
    monkeypatch.setattr(
        security_module, "admin_login_rate_limiter", rate_limit.FailedLoginRateLimiter()
    )
    config = Config("alembic.ini")
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")
    with factory() as db:
        yield db
    engine.dispose()
    if root_engine:
        with root_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root_engine.dispose()


@pytest.fixture
def client(db_session):
    with TestClient(create_app()) as client:
        yield client


@pytest.fixture
def catalog(db_session):
    category = Category(name="Десерты", slug="desserts")
    product = Product(
        name="Тестовый десерт <b>",
        slug="bento-tort-klubnika-plombir",
        price=Decimal("100.75"),
        category=category,
        image_url="/static/products/bento-cake.jpg",
    )
    location = PickupLocation(name="Тестовая точка", address="Ленина, 15", phone="+79227330330")
    db_session.add_all([category, product, location])
    db_session.commit()
    return product, location


@pytest.fixture
def legal(db_session):
    # Synthetic fixture documents are for tests only, never published on a real site.
    policy = PrivacyPolicyVersion(
        version="test-policy",
        title="Только тест",
        text="Синтетическая политика для автоматической проверки приложения.",
        is_active=True,
        published_at=utc_now(),
    )
    consent = ConsentTextVersion(
        version="test-consent",
        text="Синтетическое согласие для автоматической проверки приложения.",
        is_active=True,
        published_at=utc_now(),
    )
    policy.content_sha256 = sha256_text(policy.text)
    consent.content_sha256 = sha256_text(consent.text)
    db_session.add_all([policy, consent])
    db_session.commit()
    return policy, consent


@pytest.fixture
def payload(catalog, legal):
    product, location = catalog
    policy, consent = legal
    return dict(
        name="Тестовый клиент",
        phone="8 (922) 733-03-30",
        date=str(minimum_order_date()),
        time="12:00",
        items=[dict(product_id=product.id, quantity=2)],
        delivery_type="pickup",
        pickup_location_id=location.id,
        consent=True,
        privacy_policy_version_id=policy.id,
        consent_text_version_id=consent.id,
        idempotency_key=uuid.uuid4().hex,
        expected_total="201.50",
    )


@pytest.fixture
def users(db_session):
    hashed = password_hasher.hash("test-password-123")
    db_session.add_all(
        [
            AdminUser(username="admin", password_hash=hashed, role="admin"),
            AdminUser(username="staff", password_hash=hashed, role="staff"),
        ]
    )
    db_session.commit()
