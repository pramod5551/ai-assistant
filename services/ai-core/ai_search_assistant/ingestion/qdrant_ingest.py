"""Qdrant helpers for document-scoped ingest (replace vectors per document_id)."""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue


async def delete_points_for_documents(
    client: AsyncQdrantClient,
    collection: str,
    document_ids: list[str],
) -> None:
    """Remove existing chunks for each document before re-ingesting that document."""
    for doc_id in sorted(set(document_ids)):
        await client.delete(
            collection_name=collection,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=doc_id),
                        )
                    ]
                )
            ),
        )
