import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
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


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    products: Mapped[list["Product"]] = relationship(
        back_populates="category",
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    weight_min_grams: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    weight_max_grams: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    portions_min: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    portions_max: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    diameter_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    height_min_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    height_max_cm: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    category_id: Mapped[str] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )

    size: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    is_available_for_order: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    vk_url: Mapped[str] = mapped_column(
        String(200),
        default="",
        nullable=False,
    )

    category: Mapped["Category"] = relationship(
        back_populates="products",
    )

    showcase_items: Mapped[list["ShowcaseItem"]] = relationship(
        back_populates="product",
    )


class PickupLocation(Base):
    __tablename__ = "pickup_locations"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    showcase_items: Mapped[list["ShowcaseItem"]] = relationship(
        back_populates="pickup_location",
    )


class ShowcaseItem(Base):
    __tablename__ = "showcase_items"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    pickup_location_id: Mapped[str] = mapped_column(
        ForeignKey("pickup_locations.id"),
        nullable=False,
    )

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id"),
        nullable=False,
    )

    pickup_location: Mapped["PickupLocation"] = relationship(
        back_populates="showcase_items",
    )

    product: Mapped["Product"] = relationship(
        back_populates="showcase_items",
    )


class SiteContact(Base):
    __tablename__ = "site_contacts"

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
    )

    type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )