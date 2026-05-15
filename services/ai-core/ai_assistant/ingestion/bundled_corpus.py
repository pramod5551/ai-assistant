"""Load the repository-shipped demo corpus (``bundled_docs/manifest.json``) as chunks."""

from __future__ import annotations

from pathlib import Path

from ai_assistant.ingestion.corpus_chunk import CorpusChunk
from ai_assistant.ingestion.manifest_corpus import load_corpus_from_manifest

_BUNDLED_ROOT = Path(__file__).resolve().parent / "bundled_docs"
_MANIFEST = _BUNDLED_ROOT / "manifest.json"


def load_bundled_corpus_chunks(
    *,
    max_chars: int = 1100,
    overlap: int = 120,
) -> tuple[CorpusChunk, ...]:
    """Convenience wrapper: same manifest loader with ``docs_root`` fixed to bundled_docs."""
    return load_corpus_from_manifest(
        _MANIFEST,
        docs_root=_BUNDLED_ROOT,
        max_chars=max_chars,
        overlap=overlap,
    )
