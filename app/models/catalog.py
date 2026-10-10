from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.services.common import generate_uuid, utc_now


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("slug", name="uq_categories_slug"),)

    def __str__(self) -> str:
        return self.name

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

    products: Mapped[list["Product"]] = relationship(
        back_populates="category",
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_products_slug"),
        CheckConstraint("price >= 0", name="ck_products_price"),
        CheckConstraint(
            "weight_min_grams IS NULL OR weight_min_grams > 0", name="ck_products_weight_min_grams"
        ),
        CheckConstraint(
            "weight_max_grams IS NULL OR weight_max_grams > 0", name="ck_products_weight_max_grams"
        ),
        CheckConstraint(
            "portions_min IS NULL OR portions_min > 0", name="ck_products_portions_min"
        ),
        CheckConstraint(
            "portions_max IS NULL OR portions_max > 0", name="ck_products_portions_max"
        ),
        CheckConstraint("diameter_cm IS NULL OR diameter_cm > 0", name="ck_products_diameter_cm"),
        CheckConstraint(
            "height_min_cm IS NULL OR height_min_cm > 0", name="ck_products_height_min_cm"
        ),
        CheckConstraint(
            "height_max_cm IS NULL OR height_max_cm > 0", name="ck_products_height_max_cm"
        ),
        CheckConstraint(
            "weight_min_grams IS NULL OR weight_max_grams IS NULL OR weight_min_grams <= weight_max_grams",
            name="ck_products_weight_range",
        ),
        CheckConstraint(
            "portions_min IS NULL OR portions_max IS NULL OR portions_min <= portions_max",
            name="ck_products_portions_range",
        ),
        CheckConstraint(
            "height_min_cm IS NULL OR height_max_cm IS NULL OR height_min_cm <= height_max_cm",
            name="ck_products_height_range",
        ),
    )

    def __str__(self) -> str:
        return self.name

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

    def __str__(self) -> str:
        return f"{self.name} — {self.address}"

    weekday_hours: Mapped[str] = mapped_column(
        String(100), default="08:00–21:00", server_default="08:00–21:00", nullable=False
    )
    weekend_hours: Mapped[str] = mapped_column(
        String(100), default="09:00–21:00", server_default="09:00–21:00", nullable=False
    )

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

    showcase_items: Mapped[list["ShowcaseItem"]] = relationship(
        back_populates="pickup_location",
    )


class ShowcaseItem(Base):
    __tablename__ = "showcase_items"
    __table_args__ = (
        UniqueConstraint("pickup_location_id", "product_id", name="uq_showcase_location_product"),
    )

    id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
        default=generate_uuid,
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
