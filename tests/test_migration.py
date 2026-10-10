import os
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect, select, text

from alembic import command
from app.models import Category, Product


def test_alembic_cli_loads_complete_metadata_in_fresh_process(tmp_path):
    environment = {
        **os.environ,
        "APP_ENV": "test",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'fresh.sqlite'}",
        "EMAIL_WORKER_ENABLED": "false",
    }
    for arguments in (["upgrade", "head"], ["check"]):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            env=environment,
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_existing_data_preserved_and_preflight_is_atomic(db_session):
    engine = db_session.get_bind()
    config = Config("alembic.ini")
    stamp = datetime(2026, 9, 1, 10)
    with engine.connect() as connection:
        config.attributes["connection"] = connection
        command.downgrade(config, "6d64d4b2b21e")
        connection.execute(
            text(
                "INSERT INTO categories (id, name, slug, is_active, created_at, updated_at) VALUES (:id, :name, :slug, :active, :stamp, :stamp)"
            ),
            dict(
                id="legacy-category",
                name="Тестовая категория",
                slug="legacy-category",
                active=True,
                stamp=stamp,
            ),
        )
        connection.execute(
            text(
                "INSERT INTO products (id, name, slug, price, category_id, is_active, is_available_for_order, vk_url, created_at, updated_at) VALUES (:id, :name, :slug, :price, :category, :active, :active, :vk, :stamp, :stamp)"
            ),
            dict(
                id="legacy-product",
                name="Тестовый товар",
                slug="legacy-product",
                price=-1,
                category="legacy-category",
                active=True,
                vk="https://vk.ru/test",
                stamp=stamp,
            ),
        )
        connection.commit()
        with pytest.raises(RuntimeError, match="ck_products_price"):
            command.upgrade(config, "head")
        assert "idempotency_key" not in {
            column["name"] for column in inspect(connection).get_columns("orders")
        }
        connection.rollback()
        connection.execute(
            text("UPDATE products SET price=100.75 WHERE id=:id"), {"id": "legacy-product"}
        )
        connection.commit()
        if connection.dialect.name == "postgresql":
            connection.execute(text("SET TIME ZONE 'Europe/Moscow'"))
            connection.commit()
        command.upgrade(config, "head")
    product = db_session.scalar(select(Product).where(Product.id == "legacy-product"))
    assert product.name == "Тестовый товар" and product.price == Decimal("100.75")
    assert product.vk_url == "https://vk.ru/test"
    created = product.created_at
    if created.tzinfo is not None:
        created = created.astimezone(UTC).replace(tzinfo=None)
    assert created == stamp
    assert (
        db_session.scalar(select(Category).where(Category.id == "legacy-category")).name
        == "Тестовая категория"
    )
