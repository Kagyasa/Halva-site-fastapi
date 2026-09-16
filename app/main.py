from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers.products import router as products_router


app = FastAPI(
    title="Halva API",
    version="1.0.0",
)

app.include_router(products_router)

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "Halva API",
    }