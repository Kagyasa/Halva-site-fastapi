from datetime import date, time
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class OrderEmailRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=7, max_length=30)
    date: date
    time: time
    product_ids: list[str] = Field(min_length=1, max_length=30)
    delivery_type: Literal["pickup", "delivery"]
    pickup_location: str | None = Field(default=None, max_length=200)
    address: str | None = Field(default=None, max_length=300)
    consent: bool

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) not in (10, 11):
            raise ValueError("В номере телефона должно быть 10–11 цифр")
        return value.strip()

    @model_validator(mode="after")
    def validate_delivery_fields(self):
        if not self.consent:
            raise ValueError("Нужно согласие на обработку персональных данных")

        if self.delivery_type == "pickup" and not self.pickup_location:
            raise ValueError("Выберите точку самовывоза")

        if self.delivery_type == "delivery" and not self.address:
            raise ValueError("Укажите адрес доставки")

        return self


class OrderEmailResponse(BaseModel):
    success: bool
    message: str
    total: int
