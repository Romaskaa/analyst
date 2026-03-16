from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router


def create_fastapi_app() -> FastAPI:
    app = FastAPI()
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
