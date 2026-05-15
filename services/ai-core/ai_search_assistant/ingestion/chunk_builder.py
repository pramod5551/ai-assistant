"""Build :class:`CorpusChunk` rows from user upload payloads."""

from __future__ import annotations

from ai_search_assistant.domain.ingest_models import UploadDocument
from ai_search_assistant.ingestion.corpus_chunk import CorpusChunk
from ai_search_assistant.ingestion.text_chunker import chunk_plain_text
from ai_search_assistant.ingestion.upload_text import resolve_upload_plain_text


def _strip_front_matter(body: str) -> str:
    if "\n---\n" in body:
        return body.split("\n---\n", 1)[1]
    return body


def chunks_from_uploads(
    uploads: list[UploadDocument],
    *,
    max_chars: int = 1100,
    overlap: int = 120,
    max_upload_bytes: int = 10_485_760,
) -> tuple[CorpusChunk, ...]:
    """Chunk uploads after extracting text (PDF, DOCX, plain text, etc.)."""
    out: list[CorpusChunk] = []
    failures: list[str] = []
    for doc in uploads:
        name = doc.resolved_file_name()
        try:
            plain = resolve_upload_plain_text(doc, max_bytes=max_upload_bytes)
            body = _strip_front_matter(plain).strip()
            if not body:
                failures.append(
                    f"{name} ({doc.document_id}): no text extracted — check format or file content"
                )
                continue
            segs = chunk_plain_text(body, max_chars=max_chars, overlap=overlap)
            if not segs:
                failures.append(f"{name} ({doc.document_id}): produced no chunks")
                continue
            for seg in segs:
                out.append(
                    CorpusChunk(
                        document_id=doc.document_id,
                        title=doc.title,
                        library_id=doc.library_id,
                        text=seg,
                    )
                )
        except Exception as e:
            failures.append(f"{name} ({doc.document_id}): {e}")
    if failures:
        detail = "; ".join(failures)
        if not out:
            raise ValueError(f"No upload could be ingested. {detail}")
        raise ValueError(f"Some uploads failed. {detail}")
    return tuple(out)
