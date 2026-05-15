"""Immutable chunk row used from ingestion through vector upsert and stub retrieval."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorpusChunk:
    """One embeddable text segment with stable document and library metadata.

    Chunks sharing ``document_id`` may exist when long sources are split by :func:`chunk_plain_text`.
    """

    document_id: str
    title: str
    library_id: str
    text: str
