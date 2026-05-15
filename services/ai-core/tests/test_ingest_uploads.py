"""Tests for multi-document upload ingestion."""

from __future__ import annotations

import pytest

from ai_search_assistant.domain.ingest_models import UploadDocument
from ai_search_assistant.ingestion.chunk_builder import chunks_from_uploads
from ai_search_assistant.ingestion.corpus_chunk import CorpusChunk
from ai_search_assistant.ingestion.ingest_service import _assert_unique_document_ids
from ai_search_assistant.ingestion.point_ids import point_uuid


def test_chunks_from_uploads_multiple_documents() -> None:
    uploads = [
        UploadDocument(
            document_id="alpha-doc",
            title="Alpha",
            library_id="POLICIES",
            file_name="alpha.txt",
            content="Alpha policy text about refunds and returns.",
        ),
        UploadDocument(
            document_id="beta-doc",
            title="Beta",
            library_id="POLICIES",
            file_name="beta.txt",
            content="Beta policy text about shipping and delivery windows.",
        ),
    ]
    chunks = chunks_from_uploads(uploads)
    doc_ids = {c.document_id for c in chunks}
    assert doc_ids == {"alpha-doc", "beta-doc"}
    assert len(chunks) >= 2


def test_chunks_from_uploads_fails_on_empty_extraction() -> None:
    uploads = [
        UploadDocument(
            document_id="empty-doc",
            title="Empty",
            library_id="POLICIES",
            file_name="empty.txt",
            content="   ",
        ),
        UploadDocument(
            document_id="ok-doc",
            title="OK",
            library_id="POLICIES",
            file_name="ok.txt",
            content="Valid body text for chunking.",
        ),
    ]
    with pytest.raises(ValueError, match="Some uploads failed"):
        chunks_from_uploads(uploads)


def test_assert_unique_document_ids_rejects_duplicates() -> None:
    with pytest.raises(ValueError, match="Duplicate document_id"):
        _assert_unique_document_ids(
            [
                UploadDocument(
                    document_id="same-id",
                    title="A",
                    library_id="POLICIES",
                    content="one",
                ),
                UploadDocument(
                    document_id="same-id",
                    title="B",
                    library_id="POLICIES",
                    content="two",
                ),
            ],
        )


def test_point_uuid_differs_by_document_and_index() -> None:
    a = CorpusChunk(
        document_id="doc-a",
        title="A",
        library_id="POLICIES",
        text="shared text",
    )
    b = CorpusChunk(
        document_id="doc-b",
        title="B",
        library_id="POLICIES",
        text="shared text",
    )
    assert point_uuid("col", a, chunk_index=0) != point_uuid("col", b, chunk_index=0)
    assert point_uuid("col", a, chunk_index=0) != point_uuid("col", a, chunk_index=1)
