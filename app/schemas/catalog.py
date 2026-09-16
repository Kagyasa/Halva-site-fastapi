from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class CategorySchema(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ProductSchema(BaseModel):
    id: str
    name: str
    slug: str
    price: Decimal

    weight_min_grams: int | None = None
    weight_max_grams: int | None = None
    portions_min: int | None = None
    portions_max: int | None = None

    diameter_cm: Decimal | None = None
    height_min_cm: Decimal | None = None
    height_max_cm: Decimal | None = None

    size: str | None = None
    image_url: str | None = None
    vk_url: str

    is_active: bool
    is_available_for_order: bool

    category: CategorySchema

    model_config = ConfigDict(from_attributes=True)


class PickupLocationSchema(BaseModel):
    id: str
    name: str
    address: str
    phone: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ShowcaseItemSchema(BaseModel):
    id: str
    pickup_location: PickupLocationSchema
    product: ProductSchema

    model_config = ConfigDict(from_attributes=True)