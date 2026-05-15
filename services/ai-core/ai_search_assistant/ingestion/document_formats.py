"""Supported document extensions and human-readable labels for the ingest UI."""

from __future__ import annotations

# Extensions we attempt to parse (lowercase, with leading dot).
SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".txt",
        ".md",
        ".markdown",
        ".pdf",
        ".docx",
        ".doc",
        ".rtf",
        ".html",
        ".htm",
        ".csv",
        ".json",
        ".pptx",
    }
)

# Plain UTF-8 text — no binary parser required.
TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {".txt", ".md", ".markdown", ".csv", ".json"}
)

EXTENSION_LABELS: dict[str, str] = {
    ".txt": "Plain text",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".pdf": "PDF",
    ".docx": "Word (DOCX)",
    ".doc": "Word (DOC, legacy)",
    ".rtf": "Rich Text",
    ".html": "HTML",
    ".htm": "HTML",
    ".csv": "CSV",
    ".json": "JSON",
    ".pptx": "PowerPoint",
}

ACCEPT_ATTRIBUTE = ",".join(sorted(SUPPORTED_EXTENSIONS))


def supported_extensions() -> list[str]:
    """Sorted extension list for API responses (e.g. ``.pdf``)."""
    return sorted(SUPPORTED_EXTENSIONS)


def extension_of(filename: str) -> str:
    """Return lower-case extension including dot, or empty string."""
    if "." not in filename:
        return ""
    return ("." + filename.rsplit(".", 1)[-1]).lower()


def is_supported_filename(filename: str) -> bool:
    return extension_of(filename) in SUPPORTED_EXTENSIONS
