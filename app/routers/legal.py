from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orders import ConsentTextVersion, PrivacyPolicyVersion
from app.schemas.legal import ConsentTextSchema, PrivacyPolicySchema


router = APIRouter(
    prefix="/api/legal",
    tags=["legal"],
)


@router.get(
    "/privacy-policy/",
    response_model=PrivacyPolicySchema,
)
def get_active_privacy_policy(
    db: Session = Depends(get_db),
):
    policy = db.scalar(
        select(PrivacyPolicyVersion)
        .where(PrivacyPolicyVersion.is_active.is_(True))
        .order_by(PrivacyPolicyVersion.published_at.desc())
    )

    if policy is None:
        raise HTTPException(
            status_code=404,
            detail="Активная политика конфиденциальности не найдена",
        )

    return policy


@router.get(
    "/consent/",
    response_model=ConsentTextSchema,
)
def get_active_consent(
    db: Session = Depends(get_db),
):
    consent = db.scalar(
        select(ConsentTextVersion)
        .where(ConsentTextVersion.is_active.is_(True))
        .order_by(ConsentTextVersion.published_at.desc())
    )

    if consent is None:
        raise HTTPException(
            status_code=404,
            detail="Активный текст согласия не найден",
        )

    return consent