"""LangGraph shared state schema (``total=False`` allows incremental updates per node)."""

from __future__ import annotations

from typing import TypedDict


class GraphState(TypedDict, total=False):
    """Keys flowing through the RAG assistant graph.

    Early nodes populate ``rewritten`` and retrieval fills ``citations`` / ``retrieval_context``.
    Terminal nodes set ``answer_text`` and ``graph_path`` for debugging in responses.
    """

    message: str
    structured_output: bool
    user_libraries: tuple[str, ...]

    rewritten: str
    citations: list[dict[str, str | None]]
    retrieval_context: str
    answer_text: str
    structured: dict | None
    graph_path: str
