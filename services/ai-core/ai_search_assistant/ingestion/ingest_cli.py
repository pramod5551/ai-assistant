"""CLI: ingest plain-text files from a manifest.json on disk (advanced / batch use)."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from ai_search_assistant.domain.ingest_models import IngestOptions, IngestRequest, UploadDocument
from ai_search_assistant.ingestion.ingest_service import get_ingest_service
from ai_search_assistant.ingestion.manifest_corpus import load_corpus_from_manifest


def _bounded_int(low: int, high: int):
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


def _uploads_from_manifest(manifest: Path, docs_root: Path | None) -> list[UploadDocument]:
    """Build upload rows from manifest + on-disk text files."""
    root = docs_root if docs_root is not None else manifest.parent
    raw = manifest.read_text(encoding="utf-8")
    spec = json.loads(raw)
    uploads: list[UploadDocument] = []
    for row in spec.get("documents", []):
        path = (root / row["path"]).resolve()
        text = path.read_text(encoding="utf-8")
        uploads.append(
            UploadDocument(
                document_id=row["document_id"],
                title=row["title"],
                library_id=row["library_id"],
                file_name=path.name,
                content=text,
            )
        )
    return uploads


async def _ingest_cli(
    *,
    manifest: Path,
    docs_root: Path | None,
    batch_size: int,
    dry_run: bool,
    recreate_collection: bool,
    yes: bool,
) -> int:
    if recreate_collection and not yes:
        print("Recreate requires --yes (destructive delete).", file=sys.stderr)
        return 2

    if dry_run:
        chunks = load_corpus_from_manifest(manifest, docs_root=docs_root)
        settings = get_ingest_service().settings
        print(f"manifest={manifest}")
        print(f"chunks={len(chunks)} collection={settings.vector_collection}")
        by_doc: dict[str, int] = {}
        for c in chunks:
            by_doc[c.document_id] = by_doc.get(c.document_id, 0) + 1
        for doc_id, n in sorted(by_doc.items()):
            print(f"  {doc_id}: {n} chunk(s)")
        return 0

    uploads = _uploads_from_manifest(manifest, docs_root)
    service = get_ingest_service()
    result = await service.run(
        IngestRequest(
            uploads=uploads,
            options=IngestOptions(
                batch_size=batch_size,
                recreate_collection=recreate_collection,
                dry_run=False,
            ),
        )
    )
    print(
        f"Done: upserted {result.points_upserted} points into {result.collection!r} "
        f"({len(result.documents)} document(s))"
    )
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(
        description=(
            "Ingest documents listed in a manifest.json (plain-text files on disk). "
            "For browser uploads, use the Ingest tab in the web UI."
        ),
    )
    p.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to manifest.json listing document_id, title, library_id, path",
    )
    p.add_argument("--docs-root", type=Path, default=None)
    p.add_argument("--batch-size", type=_bounded_int(1, 256), default=32)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--recreate-collection", action="store_true")
    p.add_argument("--yes", action="store_true")
    args = p.parse_args()
    if not args.manifest.is_file():
        print(f"Manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(2)
    code = asyncio.run(
        _ingest_cli(
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
