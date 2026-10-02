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
from app.admin import setup_admin


BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Halva API",
    version="1.0.0",
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)

    # Не позволяем браузеру угадывать MIME-тип файлов.
    response.headers["X-Content-Type-Options"] = "nosniff"

    # Запрещаем открывать сайт внутри iframe.
    # Это защищает от clickjacking.
    response.headers["X-Frame-Options"] = "DENY"

    # Ограничиваем передачу Referer на сторонние сайты.
    response.headers["Referrer-Policy"] = (
        "strict-origin-when-cross-origin"
    )

    # Сайту Halva эти возможности браузера сейчас не нужны.
    response.headers["Permissions-Policy"] = (
        "camera=(), "
        "microphone=(), "
        "geolocation=()"
    )

    # Изолируем окно сайта от других origin.
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

    # Запрещаем старым плагинам вроде Flash загружать данные сайта.
    response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

    # В админке находятся заявки и персональные данные.
    # Не разрешаем браузеру сохранять такие страницы в кэше.
    if request.url.path.startswith("/admin"):
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"

    return response


setup_admin(app)

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