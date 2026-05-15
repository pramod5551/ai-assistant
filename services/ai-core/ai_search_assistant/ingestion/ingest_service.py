"""Programmatic ingestion into Qdrant (used by HTTP API and optional CLI)."""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from ai_search_assistant.config import Settings, get_settings
from ai_search_assistant.domain.ingest_models import (
    IngestCatalogResponse,
    IngestDocumentSummary,
    IngestRequest,
    IngestResponse,
    UploadDocument,
)
from ai_search_assistant.embeddings.factory import create_embedder
from ai_search_assistant.ingestion.chunk_builder import chunks_from_uploads
from ai_search_assistant.ingestion.corpus_chunk import CorpusChunk
from ai_search_assistant.ingestion.point_ids import point_uuid
from ai_search_assistant.ingestion.qdrant_ingest import delete_points_for_documents
from ai_search_assistant.search.qdrant_retriever import ensure_collection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestService:
    """Chunk, embed, and upsert user-uploaded documents."""

    settings: Settings

    async def get_catalog(self) -> IngestCatalogResponse:
        """Return ingest UI settings (formats, libraries, limits)."""
        return IngestCatalogResponse(
            collection=self.settings.vector_collection,
            vector_backend=self.settings.resolved_vector_backend(),
            max_upload_bytes=self.settings.ingest_max_upload_bytes,
        )

    async def run(self, request: IngestRequest) -> IngestResponse:
        """Ingest uploaded documents; honour dry-run and recreate flags."""
        if self.settings.resolved_vector_backend() != "qdrant":
            raise ValueError(
                "Ingest requires Qdrant. Set QDRANT_URL and VECTOR_BACKEND=qdrant (or auto)."
            )
        if not self.settings.qdrant_url:
            raise ValueError("QDRANT_URL is missing.")

        if not request.uploads:
            raise ValueError("Upload at least one document to ingest.")

        _assert_unique_document_ids(request.uploads)

        opts = request.options
        chunks = list(
            chunks_from_uploads(
                request.uploads,
                max_chars=opts.max_chars,
                overlap=opts.overlap,
                max_upload_bytes=self.settings.ingest_max_upload_bytes,
            )
        )
        if not chunks:
            raise ValueError("No text chunks produced. Check file content and selection.")

        summaries = _summarize_chunks(chunks)
        collection = self.settings.vector_collection

        if opts.dry_run:
            return IngestResponse(
                collection=collection,
                chunks_total=len(chunks),
                points_upserted=0,
                documents=summaries,
                dry_run=True,
                recreated_collection=False,
            )

        embedder = create_embedder(self.settings)
        distance = self.settings.qdrant_distance_metric()
        recreated = False
        client: AsyncQdrantClient | None = None
        try:
            client = AsyncQdrantClient(url=self.settings.qdrant_url)
            if opts.recreate_collection and await client.collection_exists(
                collection_name=collection
            ):
                await client.delete_collection(collection_name=collection)
                recreated = True
            await ensure_collection(client, embedder, collection, distance)

            doc_ids = sorted({c.document_id for c in chunks})
            await delete_points_for_documents(client, collection, doc_ids)
            logger.info(
                "Ingest replacing vectors for %s document(s): %s",
                len(doc_ids),
                ", ".join(doc_ids),
            )

            total = len(chunks)
            batch_size = opts.batch_size
            for start in range(0, total, batch_size):
                batch = chunks[start : start + batch_size]
                texts = [c.text for c in batch]
                vectors = await embedder.embed(texts)
                points: list[PointStruct] = []
                for i, chunk in enumerate(batch):
                    points.append(
                        PointStruct(
                            id=point_uuid(collection, chunk, chunk_index=start + i),
                            vector=vectors[i],
                            payload={
                                "document_id": chunk.document_id,
                                "title": chunk.title,
                                "library_id": chunk.library_id,
                                "text": chunk.text,
                            },
                        )
                    )
                await client.upsert(
                    collection_name=collection, points=points, wait=True
                )
                logger.info(
                    "Ingest upserted %s/%s points",
                    min(start + batch_size, total),
                    total,
                )
        finally:
            if client is not None:
                await client.close()

        return IngestResponse(
            collection=collection,
            chunks_total=len(chunks),
            points_upserted=len(chunks),
            documents=summaries,
            dry_run=False,
            recreated_collection=recreated,
        )


def _summarize_chunks(chunks: list[CorpusChunk]) -> list[IngestDocumentSummary]:
    by_doc: dict[str, list[CorpusChunk]] = defaultdict(list)
    for c in chunks:
        by_doc[c.document_id].append(c)
    out: list[IngestDocumentSummary] = []
    for doc_id, group in sorted(by_doc.items()):
        first = group[0]
        out.append(
            IngestDocumentSummary(
                document_id=doc_id,
                title=first.title,
                library_id=first.library_id,
                chunk_count=len(group),
                source="upload",
            )
        )
    return out


def _assert_unique_document_ids(uploads: list[UploadDocument]) -> None:
    """Reject duplicate ids so multi-file ingest does not overwrite vectors."""
    seen: set[str] = set()
    for upload in uploads:
        doc_id = upload.document_id
        if doc_id in seen:
            raise ValueError(
                f"Duplicate document_id {doc_id!r}. Each file needs a unique id."
            )
        seen.add(doc_id)


def get_ingest_service() -> IngestService:
    return IngestService(settings=get_settings())
