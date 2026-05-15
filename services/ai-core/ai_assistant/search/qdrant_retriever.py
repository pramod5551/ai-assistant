"""Qdrant vector search: collection bootstrap, demo seeding, and permission-filtered retrieval.

This module is the production counterpart to :mod:`ai_assistant.search.stub_retriever`. It uses
``AsyncQdrantClient.query_points`` (current qdrant-client API) for similarity search and applies
a payload filter so users only see chunks from libraries in ``library_access``.
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

from ai_assistant.domain.models import Citation
from ai_assistant.embeddings import Embedder
from ai_assistant.ingestion.corpus_fixtures import DEFAULT_CORPUS_CHUNKS
from ai_assistant.search.types import RetrievalResult

RFC2119_DOCUMENT_ID = "ietf-bcp14-rfc2119"

_NORMATIVE_HINT = re.compile(
    r"\b(ietf|ietf/requirements|bcp\s*14|rfc\s*2119|rfc2119|"
    r"normative\b|requirement levels)\b",
    re.IGNORECASE,
)
_MUST_AND_SHOULD = re.compile(
    r"\bmust\b.*\bshould\b|\bshould\b.*\bmust\b",
    re.IGNORECASE,
)


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


def _wants_rfc2119_boost(query: str) -> bool:
    """Heuristic: user is asking about IETF normative keywords / RFC 2119."""
    q = query.strip()
    if not q:
        return False
    if _NORMATIVE_HINT.search(q):
        return True
    if _MUST_AND_SHOULD.search(q):
        return True
    return False


def _interleave_hits_by_document(
    hits: list[Any],
    *,
    score_override: dict[str, float] | None = None,
) -> list[Any]:
    """Spread chunks across documents so one long corpus doc cannot fill the whole context window.

    Without this, many adjacent chunks from the same CISA/OWASP passage can outrank a small
    RFC 2119 chunk; local LLMs then never "see" the normative definitions before truncation.
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


async def _scroll_document_points(
    client: AsyncQdrantClient,
    collection: str,
    *,
    document_id: str,
    library_access: tuple[str, ...],
    max_points: int = 16,
) -> list[Any]:
    flt = Filter(
        must=[
            FieldCondition(
                key="library_id",
                match=MatchAny(any=list(library_access)),
            ),
            FieldCondition(
                key="document_id",
                match=MatchValue(value=document_id),
            ),
        ]
    )
    records, _next = await client.scroll(
        collection_name=collection,
        scroll_filter=flt,
        limit=max_points,
        with_payload=True,
        with_vectors=False,
    )
    return list(records)


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


async def seed_qdrant_if_empty(
    client: AsyncQdrantClient,
    embedder: Embedder,
    collection: str,
    enabled: bool,
) -> None:
    """On empty collection, upsert :data:`DEFAULT_CORPUS_CHUNKS` (optional dev/demo convenience)."""
    if not enabled:
        return
    cnt = await client.count(collection_name=collection, exact=True)
    if cnt.count > 0:
        return

    texts = [c.text for c in DEFAULT_CORPUS_CHUNKS]
    vectors = await embedder.embed(texts)
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vectors[i],
            payload={
                "document_id": chunk.document_id,
                "title": chunk.title,
                "library_id": chunk.library_id,
                "text": chunk.text,
            },
        )
        for i, chunk in enumerate(DEFAULT_CORPUS_CHUNKS)
    ]
    await client.upsert(collection_name=collection, points=points, wait=True)


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
        """Return top hits as :class:`~ai_assistant.search.types.RetrievalResult` (deduped by document)."""
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

        supplement: list[Any] = []
        if _wants_rfc2119_boost(query):
            supplement = await _scroll_document_points(
                self._client,
                self._collection,
                document_id=RFC2119_DOCUMENT_ID,
                library_access=library_access,
                max_points=16,
            )

        seen_ids: set[str] = set()
        merged: list[Any] = []
        for h in supplement + hits:
            pid = _point_id(h)
            if pid:
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
            merged.append(h)

        if not merged:
            return RetrievalResult(citations=[], context_text="")

        boost_scores: dict[str, float] = {}
        for h in supplement:
            pid = _point_id(h)
            if pid:
                boost_scores[pid] = 1e6

        interleaved = _interleave_hits_by_document(merged, score_override=boost_scores)
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
