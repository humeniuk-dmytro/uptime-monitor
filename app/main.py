import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import engine
from app.models import Base
from app.routers import history, monitors
from app.worker import run_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="URL Uptime Monitor",
    description="Periodically checks HTTP endpoints and tracks their availability",
    version="1.0.0",
)

app.include_router(monitors.router)
app.include_router(history.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.on_event("startup")
async def startup() -> None:
    logger.info("Creating database tables if not exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Starting background worker...")
    asyncio.create_task(run_worker())


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("Shutting down database engine...")
    await engine.dispose()


@app.get("/healthz", tags=["ops"])
async def healthz() -> dict:
    return {"status": "ok"}
