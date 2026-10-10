from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.catalog import SiteContact
from app.schemas.contacts import SiteContactResponse

router = APIRouter(
    prefix="/api/contacts",
    tags=["contacts"],
)


@router.get("/", response_model=list[SiteContactResponse])
def get_contacts(db: Session = Depends(get_db)) -> list[SiteContact]:
    return list(
        db.scalars(
            select(SiteContact)
            .where(SiteContact.is_active.is_(True))
            .order_by(SiteContact.type, SiteContact.created_at.desc(), SiteContact.id)
        ).all()
    )
