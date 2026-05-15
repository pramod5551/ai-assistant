"""Default retrieval corpus: real sample documents under bundled_docs/ (see SOURCES.txt)."""

from __future__ import annotations

from ai_assistant.ingestion.bundled_corpus import load_bundled_corpus_chunks
from ai_assistant.ingestion.corpus_chunk import CorpusChunk

DEFAULT_CORPUS_CHUNKS: tuple[CorpusChunk, ...] = load_bundled_corpus_chunks()

__all__ = ["CorpusChunk", "DEFAULT_CORPUS_CHUNKS"]
