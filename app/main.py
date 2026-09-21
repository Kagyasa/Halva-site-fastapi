from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routers.products import router as products_router
from app.routers.showcase import router as showcase_router
from app.routers.legal import router as legal_router
from app.routers.orders import router as orders_router
from app.routers.contacts import router as contacts_router


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Halva API",
    version="1.0.0",
)

app.mount(
    "/static",
    StaticFiles(directory=BASE_DIR / "static"),
    name="static",
)

templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)

app.include_router(products_router)
app.include_router(showcase_router)
app.include_router(legal_router)
app.include_router(orders_router)
app.include_router(contacts_router)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Halva API",
    }