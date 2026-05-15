"""Pydantic DTOs shared by HTTP layer, orchestration, and persistence.

These models mirror JSON contracts from the BFF and stable API responses.
Keep field aliases aligned with Java DTOs where ``camelCase`` is used externally.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserContext(BaseModel):
    """Identity and entitlements for the caller, derived from BFF trust headers.

    Attributes:
        subject: Stable user identifier (e.g. OIDC ``sub``).
        roles: Optional role names for future policy hooks.
        library_access: Document libraries this user may retrieve against; must align with
            vector payload ``library_id`` for Qdrant filters / stub retriever.
    """

    model_config = {"frozen": True}

    subject: str
    roles: tuple[str, ...] = ()
    library_access: tuple[str, ...] = ()


class ChatRequest(BaseModel):
    """Inbound chat turn from the BFF (mirrors public assist API body)."""

    model_config = ConfigDict(populate_by_name=True)

    message: str = Field(..., max_length=16_000, description="End-user question or instruction.")
    session_id: str | None = Field(
        default=None, max_length=128, alias="sessionId", description="Optional sticky session id."
    )
    structured_output: bool = Field(
        default=False,
        alias="structuredOutput",
        description="If true, response may include a structured block (summary, checklist, etc.).",
    )


class Citation(BaseModel):
    """A single grounded source reference returned to the client."""

    document_id: str
    title: str
    library_id: str
    snippet: str | None = Field(
        default=None,
        description="Short excerpt from the chunk; may be omitted when not available.",
    )


class ChatResponse(BaseModel):
    """Assistant reply plus provenance for audit and UI citation display."""

    correlation_id: str
    answer_text: str
    structured: dict[str, Any] | None = None
    citations: list[Citation] = Field(default_factory=list)
    graph_path: str = Field(
        ...,
        description="Debug breadcrumb of LangGraph nodes traversed (e.g. rewrite→retrieve→generate).",
    )
