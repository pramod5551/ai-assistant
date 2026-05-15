"""Application service boundary for the assist use-case.

Bridges HTTP facades to the orchestration :class:`~ai_search_assistant.orchestration.contracts.AssistantPipeline`
and records audit rows after each successful completion.
"""

from __future__ import annotations

from functools import lru_cache

from ai_search_assistant.domain.models import ChatRequest, ChatResponse, UserContext
from ai_search_assistant.orchestration.contracts import AssistantPipeline
from ai_search_assistant.orchestration.rag_graph import get_pipeline
from ai_search_assistant.persistence.audit import get_audit_sink


class AssistService:
    """Coordinates pipeline execution and post-reply observability (audit sink).

    Policy hooks (quotas, PII redaction, etc.) belong here rather than in HTTP routes.
    """

    def __init__(self, pipeline: AssistantPipeline) -> None:
        self._pipeline = pipeline

    async def complete_chat(
        self, req: ChatRequest, user: UserContext, correlation_id: str
    ) -> ChatResponse:
        """Execute LangGraph and append an audit row when SQL audit is enabled.

        Audit failures are logged but do not fail the user response (see :class:`SqlAuditSink`).
        """
        response = await self._pipeline.run(req, user, correlation_id)
        await get_audit_sink().record(
            req=req, user=user, correlation_id=correlation_id, response=response
        )
        return response


@lru_cache
def get_assist_service() -> AssistService:
    """Singleton service with a cached pipeline — matches FastAPI dependency lifetime."""
    return AssistService(get_pipeline())
