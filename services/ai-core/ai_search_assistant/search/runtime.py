"""Process-local retriever wiring (Qdrant + embedder vs in-memory stub).

Module globals hold the active :class:`Retriever` after :func:`init_retrieval` runs during
application lifespan — callers should always use :func:`get_retriever` inside request handlers.
"""

from __future__ import annotations

import logging
from typing import Any

from ai_search_assistant.config import Settings
from ai_search_assistant.embeddings.factory import create_embedder
from ai_search_assistant.search.protocol import Retriever
from ai_search_assistant.search.qdrant_retriever import QdrantRetriever, ensure_collection
from ai_search_assistant.search.stub_retriever import StubRetriever

logger = logging.getLogger(__name__)

_retriever: Retriever | None = None
_qdrant_client: Any = None


def get_retriever() -> Retriever:
    """Return the retriever initialized during app lifespan."""
    if _retriever is None:
        raise RuntimeError("Retriever not initialized (lifespan did not run?)")
    return _retriever


async def init_retrieval(settings: Settings) -> None:
    """Configure stub or Qdrant backend and ensure the vector collection exists."""
    global _retriever, _qdrant_client
    mode = settings.resolved_vector_backend()
    if mode == "stub":
        _retriever = StubRetriever()
        logger.info("Vector backend: stub")
        return

    from qdrant_client import AsyncQdrantClient

    embedder = create_embedder(settings)
    _qdrant_client = AsyncQdrantClient(url=settings.qdrant_url)  # validated by resolver
    distance = settings.qdrant_distance_metric()
    await ensure_collection(
        _qdrant_client,
        embedder,
        settings.vector_collection,
        distance,
    )
    _retriever = QdrantRetriever(
        _qdrant_client,
        embedder,
        settings.vector_collection,
        settings.vector_search_limit,
    )
    logger.info(
        "Vector backend: qdrant collection=%s embedding=%s",
        settings.vector_collection,
        settings.resolved_embedding_backend(),
    )


async def shutdown_retrieval() -> None:
    """Close outbound clients (Qdrant) and drop references for clean process exit."""
    global _retriever, _qdrant_client
    if _qdrant_client is not None:
        await _qdrant_client.close()
        _qdrant_client = None
    _retriever = None
