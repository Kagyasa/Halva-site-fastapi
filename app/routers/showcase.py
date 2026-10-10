from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.catalog import Category, PickupLocation, Product, ShowcaseItem
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
    pickup_location_id: str | None = Query(default=None, max_length=64),
):
    statement = (
        select(ShowcaseItem)
        .options(
            selectinload(ShowcaseItem.pickup_location),
            selectinload(ShowcaseItem.product).selectinload(Product.category),
        )
        .where(
            ShowcaseItem.pickup_location.has(PickupLocation.is_active.is_(True)),
            ShowcaseItem.product.has(
                Product.is_active.is_(True) & Product.category.has(Category.is_active.is_(True))
            ),
        )
        .order_by(ShowcaseItem.created_at)
    )

    if pickup_location_id:
        statement = statement.where(ShowcaseItem.pickup_location_id == pickup_location_id)
    items = db.scalars(statement).all()

    return items
