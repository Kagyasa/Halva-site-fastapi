from app.routers.products import router as products_router
from app.routers.showcase import router as showcase_router
from app.routers.legal import router as legal_router

__all__ = [
    "products_router",
    "showcase_router",
    "legal_router",
]