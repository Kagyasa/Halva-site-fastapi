from fastapi import APIRouter
from sqlalchemy import select

from app.database import SessionLocal
from app.models.catalog import SiteContact
from app.schemas.contacts import SiteContactResponse


router = APIRouter(
    prefix="/api/contacts",
    tags=["contacts"],
)


@router.get("/", response_model=list[SiteContactResponse])
def get_contacts() -> list[SiteContact]:
    with SessionLocal() as db:
        contacts = db.scalars(
            select(SiteContact)
            .where(SiteContact.is_active.is_(True))
            .order_by(SiteContact.type, SiteContact.title)
        ).all()

        return list(contacts)
