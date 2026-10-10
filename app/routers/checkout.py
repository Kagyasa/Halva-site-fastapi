from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models.catalog import PickupLocation
from app.schemas.catalog import PickupLocationSchema
from app.schemas.legal import ConsentTextSchema, PrivacyPolicySchema
from app.services.common import minimum_order_date
from app.services.legal import active_documents

router = APIRouter(prefix="/api/checkout", tags=["checkout"])


class CheckoutSchema(BaseModel):
    available: bool
    demo_mode: bool
    reason: str | None
    delivery_price: Decimal
    minimum_date: date
    locations: list[PickupLocationSchema]
    privacy_policy: PrivacyPolicySchema | None
    consent_text: ConsentTextSchema | None


@router.get("/", response_model=CheckoutSchema)
def get_checkout(db: Session = Depends(get_db)):
    policy, consent = active_documents(db)
    return CheckoutSchema(
        available=bool(policy and consent),
        demo_mode=get_settings().demo_mode,
        reason=None
        if policy and consent
        else "Приём заявок станет доступен после публикации политики и согласия.",
        delivery_price=get_settings().delivery_price,
        minimum_date=minimum_order_date(),
        locations=[
            PickupLocationSchema.model_validate(location)
            for location in db.scalars(
                select(PickupLocation)
                .where(PickupLocation.is_active.is_(True))
                .order_by(PickupLocation.created_at, PickupLocation.id)
            ).all()
        ],
        privacy_policy=PrivacyPolicySchema.model_validate(policy) if policy else None,
        consent_text=ConsentTextSchema.model_validate(consent) if consent else None,
    )
