"""Stub retriever for demos or tests without a vector database.

Returns all bundled corpus chunks the user is allowed to see — ignores query text —
giving deterministic grounding without embeddings.
"""

from __future__ import annotations

from ai_assistant.domain.models import Citation
from ai_assistant.ingestion.corpus_fixtures import DEFAULT_CORPUS_CHUNKS
from ai_assistant.search.types import RetrievalResult


class StubRetriever:
    """Keyword-agnostic pass-through of fixture chunks filtered only by ``library_access``."""

    async def search(self, library_access: tuple[str, ...], _query: str) -> RetrievalResult:
        """Build citations + context from in-memory fixtures (no vector similarity)."""
        allowed = set(library_access)
        chunks = [c for c in DEFAULT_CORPUS_CHUNKS if c.library_id in allowed]
        if not chunks:
            return RetrievalResult(citations=[], context_text="")

        cite_by_doc: dict[str, Citation] = {}
        for ch in chunks:
            if ch.document_id not in cite_by_doc:
                cite_by_doc[ch.document_id] = Citation(
                    document_id=ch.document_id,
                    title=ch.title,
                    library_id=ch.library_id,
                    snippet=ch.text[:500],
                )

        context = "\n\n".join(
            f"[{c.document_id}] {c.title}\n{c.text}" for c in chunks
        )
        return RetrievalResult(citations=list(cite_by_doc.values()), context_text=context)
