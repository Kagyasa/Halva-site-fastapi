import re
from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PHONE_ALLOWED_RE = re.compile(r"^[0-9+()\-\s]+$")


def normalize_spaces(value: str) -> str:
    return " ".join(value.split())


class OrderItemRequest(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=50, strict=True)

    @field_validator("product_id", mode="before")
    @classmethod
    def normalize_product_id(cls, value):
        return value.strip() if isinstance(value, str) else value


class OrderCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=7, max_length=30)
    date: date
    time: time
    items: list[OrderItemRequest] = Field(min_length=1, max_length=30)
    delivery_type: Literal["pickup", "delivery"]
    pickup_location_id: str | None = Field(default=None, min_length=1, max_length=64)
    address: str | None = Field(default=None, max_length=300)
    website: str = Field(default="", max_length=200)
    consent: bool = Field(strict=True)
    privacy_policy_version_id: str = Field(min_length=1, max_length=64)
    consent_text_version_id: str = Field(min_length=1, max_length=64)
    expected_total: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    idempotency_key: str = Field(min_length=32, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return normalize_spaces(value) if isinstance(value, str) else value

    @field_validator("pickup_location_id", "address", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None

        if isinstance(value, str):
            normalized = normalize_spaces(value)
            return normalized or None

        return value

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone_input(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("phone")
    @classmethod
    def validate_and_normalize_phone(cls, value: str) -> str:
        if not PHONE_ALLOWED_RE.fullmatch(value):
            raise ValueError("Номер телефона содержит недопустимые символы")

        digits = "".join(ch for ch in value if ch.isdigit())

        if len(digits) == 10:
            digits = f"7{digits}"

        elif len(digits) == 11 and digits.startswith("8"):
            digits = f"7{digits[1:]}"

        elif len(digits) == 11 and digits.startswith("7"):
            pass

        else:
            raise ValueError("Укажите российский номер телефона из 10–11 цифр")

        return f"+{digits}"

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: time) -> time:
        if value.tzinfo is not None or value.second or value.microsecond:
            raise ValueError("Укажите местное время в формате ЧЧ:ММ")
        return value

    @field_validator("items")
    @classmethod
    def validate_unique_products(
        cls,
        value: list[OrderItemRequest],
    ) -> list[OrderItemRequest]:
        product_ids = [item.product_id for item in value]

        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Один товар не должен повторяться в заявке")

        return value

    @model_validator(mode="after")
    def validate_delivery_fields(self):
        if not self.consent:
            raise ValueError("Нужно согласие на обработку персональных данных")

        if self.delivery_type == "pickup" and not self.pickup_location_id:
            raise ValueError("Выберите точку самовывоза")

        if self.delivery_type == "delivery" and not self.address:
            raise ValueError("Укажите адрес доставки")

        if self.delivery_type == "pickup":
            self.address = None
        else:
            self.pickup_location_id = None
        return self


class OrderCreateResponse(BaseModel):
    success: bool
    message: str
    total: Decimal
    order_id: str


# Names retained for integrations importing the previous schema classes.
OrderEmailRequest = OrderCreateRequest
OrderEmailResponse = OrderCreateResponse
