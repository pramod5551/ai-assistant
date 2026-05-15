"""Construct a concrete :class:`~ai_search_assistant.embeddings.Embedder` from resolved settings."""

from __future__ import annotations

from ai_search_assistant.config import Settings
from ai_search_assistant.embeddings import Embedder
from ai_search_assistant.embeddings.fastembed_backend import FastembedEmbedder
from ai_search_assistant.embeddings.http_openai import OpenAICompatibleEmbedder


def create_embedder(settings: Settings) -> Embedder:
    """Dispatch on :meth:`ai_search_assistant.config.Settings.resolved_embedding_backend`.

    Raises:
        ValueError: When ``openai_compatible`` is selected but no API base URL is configured.
    """
    backend = settings.resolved_embedding_backend()
    if backend == "fastembed":
        return FastembedEmbedder(settings.embedding_model)
    base = settings.embedding_api_base
    if not base:
        raise ValueError("EMBEDDING_API_BASE is required for openai_compatible embeddings")
    return OpenAICompatibleEmbedder(
        api_base=base,
        model=settings.embedding_model,
        api_key=settings.embedding_api_key,
        timeout_seconds=settings.embedding_request_timeout_seconds,
    )
