import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Event, Thread

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app import database
from app.admin import setup_admin
from app.config import get_settings
from app.routers.checkout import router as checkout_router
from app.routers.contacts import router as contacts_router
from app.routers.legal import router as legal_router
from app.routers.orders import router as orders_router
from app.routers.products import router as products_router
from app.routers.showcase import router as showcase_router
from app.services.legal import prepare_demo_documents
from app.services.notifications import run_worker

BASE_DIR = Path(__file__).resolve().parent

settings = get_settings()

IS_PRODUCTION = settings.app_env.strip().lower() == "production"


@asynccontextmanager
async def lifespan(app):
    if settings.demo_mode:

        def prepare_demo():
            with database.SessionLocal() as db:
                prepare_demo_documents(db)

        await asyncio.to_thread(prepare_demo)
    stop = Event()
    worker = None
    if settings.email_worker_enabled:
        worker = Thread(target=run_worker, args=(stop,), daemon=True, name="email-outbox")
        worker.start()
    try:
        yield
    finally:
        stop.set()
        if worker:
            await asyncio.to_thread(worker.join, 30)


templates = Jinja2Templates(directory=BASE_DIR / "templates")


async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


async def health_check():
    return {
        "status": "ok",
        "service": "Halva API",
    }


def create_app() -> FastAPI:
    app = FastAPI(
        title="Halva API",
        lifespan=lifespan,
        version="1.0.0",
        docs_url=None if IS_PRODUCTION else "/docs",
        redoc_url=None if IS_PRODUCTION else "/redoc",
        openapi_url=None if IS_PRODUCTION else "/openapi.json",
    )

    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)

        # Не позволяем браузеру угадывать MIME-тип файлов.
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Запрещаем открывать сайт внутри iframe.
        # Это защищает от clickjacking.
        response.headers["X-Frame-Options"] = "DENY"

        # Ограничиваем передачу Referer на сторонние сайты.
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Сайту Halva эти возможности браузера сейчас не нужны.
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        # Изолируем окно сайта от других origin.
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Запрещаем старым плагинам вроде Flash загружать данные сайта.
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # В админке находятся заявки и персональные данные.
        # Не разрешаем браузеру сохранять такие страницы в кэше.
        if request.url.path.startswith(("/admin", "/api/checkout", "/api/legal", "/api/orders")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"

        if IS_PRODUCTION and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    setup_admin(app)

    app.mount(
        "/static",
        StaticFiles(directory=BASE_DIR / "static"),
        name="static",
    )

    app.include_router(checkout_router)
    app.include_router(products_router)
    app.include_router(showcase_router)
    app.include_router(legal_router)
    app.include_router(orders_router)
    app.include_router(contacts_router)

    app.add_api_route("/", home, response_class=HTMLResponse)
    app.add_api_route("/api/health", health_check)
    return app


app = create_app()
