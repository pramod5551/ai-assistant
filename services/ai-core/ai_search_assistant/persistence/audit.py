"""Audit sink implementations (null vs SQL persistence).

Selection happens in :func:`configure_audit_sink` from :meth:`Settings.resolved_audit_backend`.
Writes are best-effort: failures are logged and never break user-facing chat completion.
"""

from __future__ import annotations

import logging
from typing import Protocol

from ai_search_assistant.config import Settings
from ai_search_assistant.domain.models import ChatRequest, ChatResponse, UserContext
from ai_search_assistant.persistence.db import session_scope
from ai_search_assistant.persistence.models import AssistAudit

logger = logging.getLogger(__name__)


class AuditSink(Protocol):
    """Interface consumed by :class:`ai_search_assistant.services.assist_service.AssistService`."""

    async def record(
        self,
        *,
        req: ChatRequest,
        user: UserContext,
        correlation_id: str,
        response: ChatResponse,
    ) -> None:
        """Persist (or drop) a single assist interaction record."""
        ...


class NullAuditSink:
    """No-op implementation when auditing is disabled."""

    async def record(
        self,
        *,
        req: ChatRequest,
        user: UserContext,
        correlation_id: str,
        response: ChatResponse,
    ) -> None:
        return None


class SqlAuditSink:
    """Append-only INSERTs via SQLAlchemy using whichever async driver ``DATABASE_URL`` selects."""

    async def record(
        self,
        *,
        req: ChatRequest,
        user: UserContext,
        correlation_id: str,
        response: ChatResponse,
    ) -> None:
        preview_max = 2000
        row = AssistAudit(
            correlation_id=correlation_id,
            user_sub=user.subject,
            roles=list(user.roles),
            library_access=list(user.library_access),
            message_preview=req.message[:preview_max],
            answer_preview=response.answer_text[:preview_max],
            graph_path=response.graph_path,
            structured_output=req.structured_output,
            citation_count=len(response.citations),
            citation_doc_ids=[c.document_id for c in response.citations] or None,
        )
        try:
            async with session_scope() as session:
                session.add(row)
        except Exception:
            logger.exception("Audit write failed for correlation_id=%s", correlation_id)


_sink: AuditSink = NullAuditSink()


def configure_audit_sink(settings: Settings) -> None:
    """Swap global sink based on resolved audit mode (``none`` vs ``sql``)."""
    global _sink
    mode = settings.resolved_audit_backend()
    _sink = SqlAuditSink() if mode == "sql" else NullAuditSink()


def get_audit_sink() -> AuditSink:
    """Accessor for dependency-free modules (services layer)."""
    return _sink
