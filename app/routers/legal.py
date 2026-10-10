from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orders import ConsentTextVersion, PrivacyPolicyVersion
from app.schemas.legal import ConsentTextSchema, PrivacyPolicySchema
from app.services.legal import active_document

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
    policy = active_document(db, PrivacyPolicyVersion)

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
    consent = active_document(db, ConsentTextVersion)

    if consent is None:
        raise HTTPException(
            status_code=404,
            detail="Активный текст согласия не найден",
        )

    return consent
