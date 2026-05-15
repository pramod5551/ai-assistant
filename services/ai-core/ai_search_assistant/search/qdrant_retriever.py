"""Qdrant vector search: collection bootstrap, demo seeding, and permission-filtered retrieval.

This module is the production counterpart to :mod:`ai_search_assistant.search.stub_retriever`. It uses
``AsyncQdrantClient.query_points`` (current qdrant-client API) for similarity search and applies
a payload filter so users only see chunks from libraries in ``library_access``.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    VectorParams,
)

from ai_search_assistant.domain.models import Citation
from ai_search_assistant.embeddings import Embedder
from ai_search_assistant.search.types import RetrievalResult


def _point_score(hit: Any) -> float:
    """Normalize optional score attribute on query hit objects (missing → 0.0)."""
    s = getattr(hit, "score", None)
    return float(s) if s is not None else 0.0


def _point_payload(hit: Any) -> dict[str, Any]:
    """Return hit payload as a plain dict (Pydantic ``model_dump`` or mapping coercion)."""
    p = getattr(hit, "payload", None)
    if p is None:
        return {}
    if isinstance(p, dict):
        return p
    if hasattr(p, "model_dump"):
        return p.model_dump()
    return dict(p)


async def _query_similar(
    client: AsyncQdrantClient,
    collection: str,
    vector: list[float],
    flt: Filter,
    limit: int,
) -> list[Any]:
    """Run similarity search with payload; uses ``query_points`` (replaces deprecated ``search``)."""
    resp = await client.query_points(
        collection_name=collection,
        query=vector,
        query_filter=flt,
        limit=limit,
        with_payload=True,
    )
    return list(resp.points)


def _point_id(hit: Any) -> str:
    raw = getattr(hit, "id", None)
    return str(raw) if raw is not None else ""


def _interleave_hits_by_document(
    hits: list[Any],
    *,
    score_override: dict[str, float] | None = None,
) -> list[Any]:
    """Spread chunks across documents so one long corpus doc cannot fill the whole context window.

    Without this, many adjacent chunks from one long document can fill the whole context window.
    """

    def eff_score(h: Any) -> float:
        pid = _point_id(h)
        if score_override and pid and pid in score_override:
            return score_override[pid]
        return _point_score(h)

    if not hits:
        return []
    by_doc: dict[str, list[Any]] = defaultdict(list)
    for h in hits:
        doc = str(_point_payload(h).get("document_id") or "")
        by_doc[doc or "_"].append(h)
    for lst in by_doc.values():
        lst.sort(key=eff_score, reverse=True)

    doc_order = sorted(
        by_doc.keys(),
        key=lambda d: eff_score(by_doc[d][0]) if by_doc[d] else 0.0,
        reverse=True,
    )
    out: list[Any] = []
    round_idx = 0
    while len(out) < len(hits):
        progressed = False
        for d in doc_order:
            lst = by_doc[d]
            if round_idx < len(lst):
                out.append(lst[round_idx])
                progressed = True
        if not progressed:
            break
        round_idx += 1
    return out


async def ensure_collection(
    client: AsyncQdrantClient,
    embedder: Embedder,
    collection: str,
    distance: Distance,
) -> None:
    """Create the collection if missing, inferring vector size from a one-string embed probe."""
    if await client.collection_exists(collection_name=collection):
        return
    probe = await embedder.embed(["dimension-probe"])
    dim = len(probe[0])
    await client.create_collection(
        collection_name=collection,
        vectors_config=VectorParams(size=dim, distance=distance),
    )


class QdrantRetriever:
    """Embed query text, search Qdrant with library filter, build citations + LLM context string."""

    def __init__(
        self,
        client: AsyncQdrantClient,
        embedder: Embedder,
        collection: str,
        search_limit: int,
    ) -> None:
        self._client = client
        self._embedder = embedder
        self._collection = collection
        self._limit = search_limit

    async def search(self, library_access: tuple[str, ...], query: str) -> RetrievalResult:
        """Return top hits as :class:`~ai_search_assistant.search.types.RetrievalResult` (deduped by document)."""
        if not library_access:
            return RetrievalResult(citations=[], context_text="")
        if not query.strip():
            return RetrievalResult(citations=[], context_text="")

        vec = (await self._embedder.embed([query]))[0]
        flt = Filter(
            must=[
                FieldCondition(
                    key="library_id",
                    match=MatchAny(any=list(library_access)),
                )
            ]
        )
        fetch_cap = min(
            max(self._limit * 4, 32),
            100,
        )
        hits = await _query_similar(
            self._client,
            self._collection,
            vec,
            flt,
            fetch_cap,
        )

        if not hits:
            return RetrievalResult(citations=[], context_text="")

        interleaved = _interleave_hits_by_document(hits)
        max_chunks = min(len(interleaved), max(self._limit * 2, 20))
        ordered = interleaved[:max_chunks]
        context_lines: list[str] = []
        for h in ordered:
            pl = _point_payload(h)
            context_lines.append(
                f"[{pl.get('document_id')}] {pl.get('title')}\n{pl.get('text')}"
            )
        context = "\n\n".join(context_lines)

        citations: list[Citation] = []
        seen: set[str] = set()
        for h in ordered:
            pl = _point_payload(h)
            doc = str(pl.get("document_id") or "")
            if not doc or doc in seen:
                continue
            seen.add(doc)
            text = str(pl.get("text") or "")
            citations.append(
                Citation(
                    document_id=doc,
                    title=str(pl.get("title") or ""),
                    library_id=str(pl.get("library_id") or ""),
                    snippet=text[:500],
                )
            )

        return RetrievalResult(citations=citations, context_text=context)
