"""Async SQLAlchemy engine lifecycle and session factory.

URL scheme drives pooling: SQLite uses :class:`~sqlalchemy.pool.StaticPool` for file-backed
dev databases; network DBs use pre-ping + queue pool defaults suitable for modest concurrency.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import ai_search_assistant.persistence.models  # noqa: F401 — register models on Base.metadata
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from ai_search_assistant.persistence import Base

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-global async engine (must call :func:`init_database` first)."""
    if _engine is None:
        raise RuntimeError("Database not initialized; call init_database first")
    return _engine


def _engine_kwargs(url: str) -> dict:
    """Driver-specific options so SQLite, Postgres, MySQL, etc. work reliably."""
    if url.startswith("sqlite"):
        return {
            "echo": False,
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }
    return {
        "echo": False,
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
    }


async def init_database(url: str) -> None:
    """Create engine, session factory, and ``CREATE TABLE`` for registered models."""
    global _engine, _session_factory
    _engine = create_async_engine(url, **_engine_kwargs(url))
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema ready url_scheme=%s", url.split(":", 1)[0])


async def shutdown_database() -> None:
    """Dispose connections; safe to call multiple times if guarded externally."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connections closed")


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Provide a transactional scope — commits on success, rolls back on exception."""
    if _session_factory is None:
        raise RuntimeError("No session factory")
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
