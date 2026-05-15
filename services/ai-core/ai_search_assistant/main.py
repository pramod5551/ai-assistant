"""FastAPI application factory and ASGI entrypoint.

Bootstraps persistence, retrieval (vector store), optional OpenTelemetry, and routes.
The ``app`` instance is what Uvicorn serves (see ``pyproject`` script / Docker ``CMD``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_search_assistant.api.routes import assist, health, ingest
from ai_search_assistant.config import get_settings
from ai_search_assistant.middleware.correlation import CorrelationIdMiddleware
from ai_search_assistant.persistence.audit import configure_audit_sink
from ai_search_assistant.persistence.db import init_database, shutdown_database
from ai_search_assistant.search.runtime import init_retrieval, shutdown_retrieval
from ai_search_assistant.telemetry.setup import (
    init_telemetry_providers,
    instrument_fastapi_app,
    shutdown_telemetry_providers,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Wire startup/shutdown: SQL audit DB, audit sink, Qdrant/stub retrieval, then cleanup."""
    settings = get_settings()
    if settings.resolved_audit_backend() == "sql":
        db_url = settings.database_url
        if not db_url:
            raise RuntimeError("Audit backend is sql but DATABASE_URL is not set.")
        await init_database(db_url)
    configure_audit_sink(settings)
    await init_retrieval(settings)
    yield
    await shutdown_retrieval()
    if settings.resolved_audit_backend() == "sql":
        await shutdown_database()
    shutdown_telemetry_providers()


def create_app() -> FastAPI:
    """Build FastAPI with middleware, routers, and OTel HTTP instrumentation when enabled."""
    settings = get_settings()
    init_telemetry_providers(settings)
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(CorrelationIdMiddleware)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(health.router)
    app.include_router(assist.router)
    app.include_router(ingest.router)
    instrument_fastapi_app(app, settings)
    return app


# ASGI app for Uvicorn: ``uvicorn ai_search_assistant.main:app``
app = create_app()
