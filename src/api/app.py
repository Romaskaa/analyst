from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .router import router

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

def create_fastapi_app() -> FastAPI:
    app = FastAPI()
    setup_middleware(app)
    setup_frontend(app)
    app.include_router(router)
    return app

def setup_frontend(app: FastAPI) -> None:
    app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")

    @app.get("/", include_in_schema=False)
    async def frontend() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

def setup_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
