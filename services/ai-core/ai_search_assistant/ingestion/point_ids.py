"""Stable Qdrant point ids for corpus chunks."""

from __future__ import annotations

import hashlib
import uuid

from ai_search_assistant.ingestion.corpus_chunk import CorpusChunk


def point_uuid(collection: str, chunk: CorpusChunk, *, chunk_index: int = 0) -> str:
    """Deterministic id from collection, document metadata, index, and chunk text."""
    h = hashlib.sha256(
        f"{collection}\0{chunk.library_id}\0{chunk.document_id}\0{chunk_index}\0"
        f"{chunk.text}".encode("utf-8")
    ).hexdigest()
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ai-search-assistant:{h}"))
