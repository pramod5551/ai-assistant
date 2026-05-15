"""Local embedding backend using `fastembed` (lazy model load, CPU-bound work off event loop)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _to_vector(raw: Any) -> list[float]:
    """Convert numpy array or sequence to plain ``list[float]`` for Qdrant / JSON."""
    if hasattr(raw, "tolist"):
        return raw.tolist()
    return list(raw)


class FastembedEmbedder:
    """Local CPU embeddings via fastembed (model load and embed run off the asyncio event loop)."""

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._impl: Any = None
        self._init_lock = asyncio.Lock()

    def _create_impl(self) -> Any:
        """Instantiate TextEmbedding on a worker thread (import + disk IO)."""
        from fastembed import TextEmbedding

        return TextEmbedding(model_name=self._model_name)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed batch; first call loads model under a lock, then all embeds run in ``to_thread``."""
        if self._impl is None:
            async with self._init_lock:
                if self._impl is None:
                    logger.info("Loading FastEmbed model %s (first use; may take a minute)…", self._model_name)
                    self._impl = await asyncio.to_thread(self._create_impl)
                    logger.info("FastEmbed model %s ready", self._model_name)

        def _run() -> list[list[float]]:
            return [_to_vector(v) for v in self._impl.embed(texts)]

        return await asyncio.to_thread(_run)
