"""FastAPI application setup for ViralPanel."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from viralpanel.api.routes import router as api_router
from viralpanel.config import get_settings


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ViralPanel API",
        description="Painel de Controle e API do Pipeline Autônomo ViralPanel",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Permits local Vite frontend
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include REST API routes under /api
    app.include_router(api_router, prefix="/api")

    # Static media files serving (videos, audios, previews)
    storage_path = str(settings.storage_dir)
    if not os.path.exists(storage_path):
        os.makedirs(storage_path, exist_ok=True)

    app.mount("/media", StaticFiles(directory=storage_path), name="media")

    return app


app = create_app()
