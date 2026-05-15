"""Resolve upload payloads (plain text or base64 binary) to UTF-8 for chunking."""

from __future__ import annotations

import base64

from ai_search_assistant.domain.ingest_models import UploadDocument
from ai_search_assistant.ingestion.document_extract import extract_text_from_bytes
from ai_search_assistant.ingestion.document_formats import TEXT_EXTENSIONS, extension_of


def resolve_upload_plain_text(
    upload: UploadDocument,
    *,
    max_bytes: int,
) -> str:
    """Return normalized plain text from an upload row (text or base64 file)."""
    name = upload.resolved_file_name()

    if upload.content_base64:
        try:
            raw = base64.b64decode(upload.content_base64, validate=True)
        except Exception as e:
            raise ValueError(f"Invalid base64 for {name!r}") from e
        if len(raw) > max_bytes:
            raise ValueError(
                f"File {name!r} exceeds max size ({len(raw)} > {max_bytes} bytes)"
            )
        return extract_text_from_bytes(raw, name)

    if upload.content is not None:
        if len(upload.content.encode("utf-8")) > max_bytes:
            raise ValueError(f"Text upload {name!r} exceeds max size")
        ext = extension_of(name)
        if ext in TEXT_EXTENSIONS:
            return upload.content
        # Allow sending pre-extracted text with a binary-looking name (advanced).
        return upload.content

    raise ValueError(f"Upload {name!r} has no content or content_base64")
