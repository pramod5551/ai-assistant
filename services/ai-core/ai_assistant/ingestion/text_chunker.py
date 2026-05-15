"""Heuristic plain-text splitting for RAG chunking (no tokenizer dependency)."""

from __future__ import annotations


def chunk_plain_text(text: str, *, max_chars: int = 1100, overlap: int = 120) -> list[str]:
    """
    Split prose into overlapping segments, preferring paragraph and sentence boundaries.
    Suitable for embedding + RAG without a full tokenizer.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        if end < length:
            window = text[start:end]
            br = max(
                window.rfind("\n\n"),
                window.rfind(". "),
                window.rfind(".\n"),
                window.rfind("\n"),
            )
            if br >= max_chars // 2:
                end = start + br + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks
