import json
from pathlib import Path

import pytest

from ai_search_assistant.ingestion.manifest_corpus import load_corpus_from_manifest


def test_load_corpus_from_manifest_strips_preamble(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.txt").write_text(
        "Source: test\n\n---\n\nBody line one.\n\nBody line two.\n", encoding="utf-8"
    )
    manifest = root / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "path": "a.txt",
                        "document_id": "doc-a",
                        "title": "Title A",
                        "library_id": "LIB1",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    chunks = load_corpus_from_manifest(manifest)
    joined = " ".join(c.text for c in chunks)
    assert "Source: test" not in joined
    assert "Body line" in joined
    assert all(c.document_id == "doc-a" for c in chunks)
    assert all(c.library_id == "LIB1" for c in chunks)


def test_path_traversal_rejected(tmp_path: Path) -> None:
    root = tmp_path / "docs"
    root.mkdir()
    manifest = root / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "documents": [
                    {
                        "path": "../evil.txt",
                        "document_id": "x",
                        "title": "t",
                        "library_id": "L",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "evil.txt").write_text("nope", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes"):
        load_corpus_from_manifest(manifest, docs_root=root)

