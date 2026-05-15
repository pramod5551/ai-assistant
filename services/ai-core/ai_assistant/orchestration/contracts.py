"""Typing protocol for pluggable orchestration backends (LangGraph today, others tomorrow)."""

from __future__ import annotations

from typing import Protocol

from ai_assistant.domain.models import ChatRequest, ChatResponse, UserContext


class AssistantPipeline(Protocol):
    """Minimal interface the :class:`ai_assistant.services.assist_service.AssistService` needs."""

    async def run(
        self, req: ChatRequest, user: UserContext, correlation_id: str
    ) -> ChatResponse:
        """Produce a fully materialized chat response for API serialization."""
        ...
