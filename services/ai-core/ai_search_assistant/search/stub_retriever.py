"""Stub retriever for demos or tests without a vector database.

Returns no documents — use Qdrant + user ingest for real search.
"""

from __future__ import annotations

from ai_search_assistant.search.types import RetrievalResult


class StubRetriever:
    """No-op retrieval when VECTOR_BACKEND=stub."""

    async def search(
        self, library_access: tuple[str, ...], _query: str
    ) -> RetrievalResult:
        _ = library_access
        return RetrievalResult(citations=[], context_text="")
