"""Tests for multi-format document text extraction."""

from __future__ import annotations

import base64

import pytest

from ai_search_assistant.ingestion.document_extract import (
    extract_text_from_bytes,
    is_supported_filename,
    normalize_extracted_text,
    supported_extensions,
)
from ai_search_assistant.ingestion.document_formats import extension_of
from ai_search_assistant.ingestion.upload_text import resolve_upload_plain_text
from ai_search_assistant.domain.ingest_models import UploadDocument


def test_supported_extensions_includes_office_formats() -> None:
    exts = supported_extensions()
    assert ".pdf" in exts
    assert ".docx" in exts
    assert ".doc" in exts
    assert ".pptx" in exts


def test_is_supported_filename() -> None:
    assert is_supported_filename("report.PDF")
    assert not is_supported_filename("archive.zip")


def test_extract_plain_text() -> None:
    data = b"Hello MUST and SHOULD keywords."
    text = extract_text_from_bytes(data, "note.txt")
    assert "MUST" in text


def test_extract_html() -> None:
    data = b"<html><body><h1>Title</h1><p>Body text</p></body></html>"
    text = extract_text_from_bytes(data, "page.html")
    assert "Title" in text
    assert "Body text" in text


def test_extract_rtf() -> None:
    rtf = r"{\rtf1\ansi Hello \b world\b0 .}"
    text = extract_text_from_bytes(rtf.encode("utf-8"), "doc.rtf")
    assert "Hello" in text
    assert "world" in text


def test_unsupported_extension_raises() -> None:
    with pytest.raises(ValueError, match="Unsupported"):
        extract_text_from_bytes(b"x", "file.xyz")


def test_resolve_upload_text_field() -> None:
    doc = UploadDocument(
        document_id="a",
        title="A",
        library_id="POLICIES",
        file_name="a.txt",
        content="Plain upload body.",
    )
    assert "Plain upload" in resolve_upload_plain_text(doc, max_bytes=1_000_000)


def test_resolve_upload_base64_text() -> None:
    raw = "Encoded plain text.".encode()
    doc = UploadDocument(
        document_id="b",
        title="B",
        library_id="POLICIES",
        file_name="b.txt",
        content_base64=base64.b64encode(raw).decode(),
    )
    assert "Encoded plain" in resolve_upload_plain_text(doc, max_bytes=1_000_000)


def test_normalize_collapses_blank_lines() -> None:
    assert normalize_extracted_text("a\n\n\n\nb") == "a\n\nb"
