from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.catalog import Product, ShowcaseItem
from app.schemas.catalog import ShowcaseItemSchema


router = APIRouter(
    prefix="/api/showcase",
    tags=["showcase"],
)


@router.get(
    "/",
    response_model=list[ShowcaseItemSchema],
)
def get_showcase(
    db: Session = Depends(get_db),
):
    statement = (
        select(ShowcaseItem)
        .options(
            selectinload(ShowcaseItem.pickup_location),
            selectinload(ShowcaseItem.product)
            .selectinload(Product.category),
        )
        .order_by(ShowcaseItem.created_at)
    )

    items = db.scalars(statement).all()

    return items