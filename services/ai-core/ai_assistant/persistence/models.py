"""ORM models for operator-facing audit logs."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from ai_assistant.persistence import Base


class AssistAudit(Base):
    """Append-only interaction log row (no application-level updates/deletes).

    JSON and UUID column types are portable across Postgres, SQLite, MySQL, etc.

    Attributes mirror the public assist response for quick support investigations.
    """

    __tablename__ = "assist_audit"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    user_sub: Mapped[str] = mapped_column(String(512), index=True)
    roles: Mapped[list] = mapped_column(JSON)
    library_access: Mapped[list] = mapped_column(JSON)
    message_preview: Mapped[str] = mapped_column(Text)
    answer_preview: Mapped[str] = mapped_column(Text)
    graph_path: Mapped[str] = mapped_column(String(512))
    structured_output: Mapped[bool] = mapped_column(default=False)
    citation_count: Mapped[int] = mapped_column(default=0)
    citation_doc_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
