from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.catalog import Product
from app.schemas.catalog import ProductSchema


router = APIRouter(
    prefix="/api/products",
    tags=["products"],
)


@router.get(
    "/",
    response_model=list[ProductSchema],
)
def get_products(
    db: Session = Depends(get_db),
):
    statement = (
        select(Product)
        .options(selectinload(Product.category))
        .where(Product.is_active.is_(True))
        .order_by(Product.name)
    )

    products = db.scalars(statement).all()

    return products


@router.get(
    "/available/",
    response_model=list[ProductSchema],
)
def get_available_products(
    db: Session = Depends(get_db),
):
    statement = (
        select(Product)
        .options(selectinload(Product.category))
        .where(
            Product.is_active.is_(True),
            Product.is_available_for_order.is_(True),
        )
        .order_by(Product.name)
    )

    products = db.scalars(statement).all()

    return products