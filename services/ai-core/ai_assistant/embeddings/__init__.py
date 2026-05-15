"""Embedding protocol and shared typing for vector-generation strategies."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Pluggable text→vector embedding (local FastEmbed, remote OpenAI-compatible HTTP, etc.).

    Implementations must be awaitable and preserve input ordering.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed each string; return one float list per input row."""
        ...
