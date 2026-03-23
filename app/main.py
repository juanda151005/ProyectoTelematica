from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import create_db_and_tables
from app.core.logging import setup_logging
from app.modules.messages.ws_router import router as ws_router

settings = get_settings()

STATIC_DIR = Path(__file__).resolve().parent.parent / 'static'


def create_application() -> FastAPI:
    setup_logging()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        create_db_and_tables()
        yield

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # CORS — allow frontend on same origin
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    # Redirect root to frontend
    @app.get('/', include_in_schema=False)
    def root():
        return RedirectResponse(url='/static/index.html')

    app.include_router(api_router, prefix=settings.api_prefix)
    app.include_router(ws_router)
    app.mount('/uploads', StaticFiles(directory=settings.upload_dir), name='uploads')
    app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')
    return app


app = create_application()
