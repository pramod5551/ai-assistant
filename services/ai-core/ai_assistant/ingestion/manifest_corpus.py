"""Resolve ``manifest.json`` document paths, read bodies, and emit :class:`CorpusChunk` rows."""

from __future__ import annotations

import json
from pathlib import Path

from ai_assistant.ingestion.corpus_chunk import CorpusChunk
from ai_assistant.ingestion.text_chunker import chunk_plain_text


def load_corpus_from_manifest(
    manifest_path: Path,
    *,
    docs_root: Path | None = None,
    max_chars: int = 1100,
    overlap: int = 120,
) -> tuple[CorpusChunk, ...]:
    """
    Load plain-text / markdown bodies listed in manifest.json and chunk them
    for embedding. Paths in the manifest are resolved relative to docs_root,
    defaulting to the manifest file's directory.
    """
    root = docs_root if docs_root is not None else manifest_path.parent
    raw = manifest_path.read_text(encoding="utf-8")
    spec = json.loads(raw)
    out: list[CorpusChunk] = []
    for row in spec.get("documents", []):
        path = row["path"]
        doc_id = row["document_id"]
        title = row["title"]
        library_id = row["library_id"]
        full_path = (root / path).resolve()
        try:
            full_path.relative_to(root.resolve())
        except ValueError as e:
            raise ValueError(f"Path escapes docs root: {path}") from e
        body = full_path.read_text(encoding="utf-8")
        if "\n---\n" in body:
            body = body.split("\n---\n", 1)[1]
        for seg in chunk_plain_text(body, max_chars=max_chars, overlap=overlap):
            out.append(
                CorpusChunk(
                    document_id=doc_id,
                    title=title,
                    library_id=library_id,
                    text=seg,
                )
            )
    return tuple(out)
