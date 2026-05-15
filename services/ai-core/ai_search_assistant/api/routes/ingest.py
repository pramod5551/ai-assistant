"""Internal ingest HTTP API (BFF → ai-core)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ai_search_assistant.api.deps import require_internal_token
from ai_search_assistant.domain.ingest_models import (
    IngestCatalogResponse,
    IngestRequest,
    IngestResponse,
)
from ai_search_assistant.ingestion.ingest_service import IngestService, get_ingest_service

router = APIRouter(prefix="/internal/v1/ingest", tags=["ingest"])


@router.get("/catalog", response_model=IngestCatalogResponse)
async def ingest_catalog(
    _auth: Annotated[None, Depends(require_internal_token)],
    service: Annotated[IngestService, Depends(get_ingest_service)],
) -> IngestCatalogResponse:
    """Return ingest UI settings (supported formats, libraries, limits)."""
    return await service.get_catalog()


@router.post("/run", response_model=IngestResponse)
async def ingest_run(
    _auth: Annotated[None, Depends(require_internal_token)],
    body: IngestRequest,
    service: Annotated[IngestService, Depends(get_ingest_service)],
) -> IngestResponse:
    """Chunk, embed, and upsert selected documents into Qdrant."""
    try:
        return await service.run(body)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
