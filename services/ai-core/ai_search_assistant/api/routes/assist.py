"""Internal assist HTTP API (called only by the BFF, not public browsers).

Path prefix ``/internal/v1`` is intentional: the Spring BFF exposes the public
``/api/v1/assist`` contract and forwards here with additional security headers.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ai_search_assistant.api.deps import get_correlation_id, get_user_context, require_internal_token
from ai_search_assistant.domain.models import ChatRequest, ChatResponse, UserContext
from ai_search_assistant.services.assist_service import AssistService, get_assist_service

router = APIRouter(prefix="/internal/v1/assist", tags=["assist"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    _auth: Annotated[None, Depends(require_internal_token)],
    body: ChatRequest,
    request: Request,
    user: Annotated[UserContext, Depends(get_user_context)],
    correlation_id: Annotated[str, Depends(get_correlation_id)],
    service: Annotated[AssistService, Depends(get_assist_service)],
) -> ChatResponse:
    """Run the full orchestration pipeline (RAG graph) and persist audit when configured."""
    _ = request
    return await service.complete_chat(body, user, correlation_id)
