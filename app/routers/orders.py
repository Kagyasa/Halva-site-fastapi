from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.orders import OrderCreateRequest, OrderCreateResponse
from app.services.orders import save_order

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("/", response_model=OrderCreateResponse)
def create_order(data: OrderCreateRequest, request: Request, db: Session = Depends(get_db)):
    return save_order(
        db,
        data,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "")[:1000],
    )
