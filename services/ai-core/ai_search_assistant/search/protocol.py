"""Retriever abstraction: swap Qdrant, stub, or future vector DBs without changing the graph."""

from __future__ import annotations

from typing import Protocol

from ai_search_assistant.search.types import RetrievalResult


class Retriever(Protocol):
    """Asynchronous semantic search over chunk payloads scoped by ``library_access``."""

    async def search(self, library_access: tuple[str, ...], query: str) -> RetrievalResult:
        """Return ranked citations plus merged context text for LLM grounding."""
        ...
