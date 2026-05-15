"""Lightweight datatypes for retrieval outputs (kept decoupled from Qdrant types)."""

from __future__ import annotations

from dataclasses import dataclass

from ai_assistant.domain.models import Citation


@dataclass(frozen=True)
class RetrievalResult:
    """One retrieval call's worth of structured data for downstream LLM prompting.

    Attributes:
        citations: Deduped document-level refs for the API ``citations`` array.
        context_text: Flattened chunk bodies inserted into the LLM system/user envelope.
    """

    citations: list[Citation]
    context_text: str
