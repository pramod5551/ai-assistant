"""HTTP contracts for configurable document ingestion."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from ai_search_assistant.ingestion.document_formats import (
    ACCEPT_ATTRIBUTE,
    EXTENSION_LABELS,
    supported_extensions,
)


class IngestCatalogResponse(BaseModel):
    """Upload settings and backend metadata for the ingest UI."""

    libraries: list[str] = Field(
        default_factory=lambda: ["POLICIES", "PROCEDURES", "EXTERNAL_REF"]
    )
    collection: str
    vector_backend: str
    supported_extensions: list[str] = Field(
        default_factory=supported_extensions,
        description="File extensions the ingest pipeline can parse.",
    )
    supported_formats: list[str] = Field(
        default_factory=lambda: [
            EXTENSION_LABELS.get(ext, ext) for ext in supported_extensions()
        ],
    )
    accept_file_types: str = Field(
        default=ACCEPT_ATTRIBUTE,
        description="Value for HTML input accept attribute.",
    )
    max_upload_bytes: int = Field(
        default=10_485_760,
        description="Maximum raw file size per upload (10 MiB default).",
    )


class UploadDocument(BaseModel):
    """User upload: UTF-8 text and/or base64-encoded binary (PDF, DOCX, …)."""

    document_id: str = Field(..., max_length=128)
    title: str = Field(..., max_length=512)
    library_id: str = Field(..., max_length=64)
    file_name: str | None = Field(
        default=None,
        max_length=255,
        description="Original filename; used to pick parser (.pdf, .docx, …).",
    )
    content: str | None = Field(
        default=None,
        max_length=2_000_000,
        description="Plain text for .txt/.md or pre-extracted body.",
    )
    content_base64: str | None = Field(
        default=None,
        max_length=14_000_000,
        description="Base64 file bytes for binary formats (PDF, Office, …).",
    )

    @model_validator(mode="after")
    def _require_payload(self) -> UploadDocument:
        if not self.content and not self.content_base64:
            raise ValueError("Each upload needs content or content_base64")
        return self

    def resolved_file_name(self) -> str:
        if self.file_name and self.file_name.strip():
            return self.file_name.strip()
        ext = ".txt"
        if self.content_base64:
            ext = ".pdf"
        return f"{self.document_id}{ext}"


class IngestOptions(BaseModel):
    """Chunking and Qdrant write behaviour."""

    batch_size: int = Field(default=32, ge=1, le=256)
    max_chars: int = Field(default=1100, ge=200, le=8000)
    overlap: int = Field(default=120, ge=0, le=2000)
    recreate_collection: bool = False
    dry_run: bool = False


class IngestRequest(BaseModel):
    """Run ingestion for one or more user uploads."""

    uploads: list[UploadDocument] = Field(default_factory=list)
    options: IngestOptions = Field(default_factory=IngestOptions)


class IngestDocumentSummary(BaseModel):
    document_id: str
    title: str
    library_id: str
    chunk_count: int
    source: str = "upload"


class IngestResponse(BaseModel):
    """Outcome of ingest or dry-run."""

    collection: str
    chunks_total: int
    points_upserted: int
    documents: list[IngestDocumentSummary]
    dry_run: bool
    recreated_collection: bool
