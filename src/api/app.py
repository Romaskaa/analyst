from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..agents.rag import delete_old_data
from .routers import router


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        delete_old_data,
        trigger="interval",
        hours=1,
        args=[3],
    )
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


def create_fastapi_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    setup_middleware(app)
    app.include_router(router)
    return app


def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
