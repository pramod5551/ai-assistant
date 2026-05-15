"""Upsert manifest-listed documents into Qdrant (batch embed + upsert)."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import sys
import uuid
from pathlib import Path

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

from ai_assistant.config import get_settings
from ai_assistant.embeddings.factory import create_embedder
from ai_assistant.ingestion.corpus_chunk import CorpusChunk
from ai_assistant.ingestion.manifest_corpus import load_corpus_from_manifest
from ai_assistant.search.qdrant_retriever import ensure_collection

logger = logging.getLogger(__name__)

_DEFAULT_MANIFEST = Path(__file__).resolve().parent / "bundled_docs" / "manifest.json"


def _bounded_int(low: int, high: int):
    """``argparse`` ``type=`` factory: parse int and enforce ``low <= value <= high``."""

    def _parse(s: str) -> int:
        try:
            v = int(s)
        except ValueError as e:
            raise argparse.ArgumentTypeError(f"invalid int: {s!r}") from e
        if not (low <= v <= high):
            raise argparse.ArgumentTypeError(
                f"expected integer in [{low}, {high}], got {v}"
            )
        return v

    return _parse


def _point_uuid(collection: str, chunk: CorpusChunk) -> str:
    """Stable id from collection + library + document + exact chunk text."""
    h = hashlib.sha256(
        f"{collection}\0{chunk.library_id}\0{chunk.document_id}\0{chunk.text}".encode("utf-8")
    ).hexdigest()
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ai-assistant:{h}"))


async def _ingest(
    *,
    manifest: Path,
    docs_root: Path | None,
    batch_size: int,
    dry_run: bool,
    recreate_collection: bool,
    yes: bool,
) -> int:
    """Run manifest load, optional destructive recreate, batched embed+upsert; exit code for CLI."""
    settings = get_settings()
    if settings.resolved_vector_backend() != "qdrant":
        print(
            "Ingest requires Qdrant: set QDRANT_URL and VECTOR_BACKEND=qdrant (or auto).",
            file=sys.stderr,
        )
        return 2
    qdrant_url = settings.qdrant_url
    if not qdrant_url:
        print("QDRANT_URL is missing.", file=sys.stderr)
        return 2

    collection = settings.vector_collection
    chunks = load_corpus_from_manifest(
        manifest,
        docs_root=docs_root,
    )
    if dry_run:
        print(f"manifest={manifest}")
        print(f"chunks={len(chunks)} collection={collection}")
        by_doc: dict[str, int] = {}
        for c in chunks:
            by_doc[c.document_id] = by_doc.get(c.document_id, 0) + 1
        for doc_id, n in sorted(by_doc.items()):
            print(f"  {doc_id}: {n} chunk(s)")
        return 0

    if recreate_collection and not yes:
        print("Recreate requires --yes (destructive delete).", file=sys.stderr)
        return 2

    embedder = create_embedder(settings)
    distance = settings.qdrant_distance_metric()
    total = len(chunks)

    client: AsyncQdrantClient | None = None
    try:
        client = AsyncQdrantClient(url=qdrant_url)
        if recreate_collection and await client.collection_exists(collection_name=collection):
            await client.delete_collection(collection_name=collection)
        await ensure_collection(client, embedder, collection, distance)

        for start in range(0, total, batch_size):
            batch = chunks[start : start + batch_size]
            texts = [c.text for c in batch]
            vectors = await embedder.embed(texts)
            points: list[PointStruct] = []
            for i, chunk in enumerate(batch):
                points.append(
                    PointStruct(
                        id=_point_uuid(collection, chunk),
                        vector=vectors[i],
                        payload={
                            "document_id": chunk.document_id,
                            "title": chunk.title,
                            "library_id": chunk.library_id,
                            "text": chunk.text,
                        },
                    )
                )
            await client.upsert(collection_name=collection, points=points, wait=True)
            logger.info("Upserted %s/%s points", min(start + batch_size, total), total)
    finally:
        if client is not None:
            await client.close()

    print(f"Done: upserted {total} points into {collection!r}")
    return 0


def main() -> None:
    """Parse argv and run :func:`_ingest` under ``asyncio.run``."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(
        description="Chunk + embed + upsert manifest documents into Qdrant.",
    )
    p.add_argument(
        "--manifest",
        type=Path,
        default=_DEFAULT_MANIFEST,
        help="manifest.json path (default: bundled_docs/manifest.json)",
    )
    p.add_argument(
        "--docs-root",
        type=Path,
        default=None,
        help="Directory paths in the manifest resolve against this (default: manifest directory)",
    )
    p.add_argument(
        "--batch-size",
        type=_bounded_int(1, 256),
        default=32,
        help="Embed/upsert batch size (1–256, default 32)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print chunk counts only; do not call Qdrant.",
    )
    p.add_argument(
        "--recreate-collection",
        action="store_true",
        help="Delete the target collection before ingest (requires --yes).",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Confirm destructive operations.",
    )
    args = p.parse_args()
    if not args.manifest.is_file():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(2)
    code = asyncio.run(
        _ingest(
            manifest=args.manifest.resolve(),
            docs_root=args.docs_root.resolve() if args.docs_root else None,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            recreate_collection=args.recreate_collection,
            yes=args.yes,
        )
    )
    sys.exit(code)


if __name__ == "__main__":
    main()
