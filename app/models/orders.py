import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_uuid() -> str:
    return uuid.uuid4().hex


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PrivacyPolicyVersion(Base):
    __tablename__ = "privacy_policy_versions"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
    )

    version: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class ConsentTextVersion(Base):
    __tablename__ = "consent_text_versions"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
    )

    version: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    content_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
    )

    customer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    requested_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    requested_time: Mapped[time] = mapped_column(
        nullable=False,
    )

    delivery_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    pickup_location_id: Mapped[str | None] = mapped_column(
        ForeignKey("pickup_locations.id"),
        nullable=True,
    )

    delivery_address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    delivery_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=0,
        nullable=False,
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="new",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )

    consent_event: Mapped["ConsentEvent | None"] = relationship(
        back_populates="order",
        uselist=False,
        cascade="all, delete-orphan",
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
    )

    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )

    product_id: Mapped[str | None] = mapped_column(
        ForeignKey("products.id"),
        nullable=True,
    )

    product_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    order: Mapped["Order"] = relationship(
        back_populates="items",
    )


class ConsentEvent(Base):
    __tablename__ = "consent_events"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
    )

    order_id: Mapped[str] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    privacy_policy_version_id: Mapped[str] = mapped_column(
        ForeignKey("privacy_policy_versions.id"),
        nullable=False,
    )

    consent_text_version_id: Mapped[str] = mapped_column(
        ForeignKey("consent_text_versions.id"),
        nullable=False,
    )

    consent_checked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    consented_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    policy_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    consent_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    evidence_signature: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    order: Mapped["Order"] = relationship(
        back_populates="consent_event",
    )