"""LangGraph RAG pipeline: rewrite → retrieve → (clarify | generate).

Nodes emit partial state updates; :class:`LangGraphAssistantPipeline` wraps compilation,
OpenTelemetry spans, and timing histograms. Retrieval uses :func:`ai_search_assistant.search.runtime.get_retriever`.
"""

from __future__ import annotations

import time
from functools import lru_cache

from langgraph.graph import END, StateGraph
from opentelemetry import metrics, trace
from opentelemetry.trace import Status, StatusCode

from ai_search_assistant.config import get_settings
from ai_search_assistant.domain.models import ChatRequest, ChatResponse, Citation, UserContext
from ai_search_assistant.llm.openai_compatible import generate_grounded_answer
from ai_search_assistant.orchestration.contracts import AssistantPipeline
from ai_search_assistant.orchestration.graph_state import GraphState
from ai_search_assistant.search.runtime import get_retriever

_tracer = trace.get_tracer(__name__)
_meter = metrics.get_meter(__name__)
_pipeline_duration = _meter.create_histogram(
    "ai_search_assistant.pipeline.duration",
    unit="s",
    description="Wall-clock time for LangGraph assist pipeline",
)


async def _rewrite(state: GraphState) -> dict:
    """Normalize user message length; pass through as ``rewritten`` for retrieval."""
    with _tracer.start_as_current_span("rag.rewrite"):
        text = (state.get("message") or "").strip()
        if len(text) > 4_000:
            text = text[:4_000]
        return {"rewritten": text, "graph_path": "rewrite"}


async def _retrieve(state: GraphState) -> dict:
    """Call retriever with user libraries + rewritten query; store citations + context."""
    settings = get_settings()
    with _tracer.start_as_current_span("rag.retrieve") as span:
        q = state.get("rewritten") or ""
        libs = state.get("user_libraries") or ()
        span.set_attribute("rag.query.length", len(q))
        span.set_attribute("rag.libraries.count", len(libs))
        span.set_attribute("qdrant.collection", settings.vector_collection)
        hits = await get_retriever().search(libs, q)
        span.set_attribute("rag.citations.count", len(hits.citations))
        payload = [c.model_dump() for c in hits.citations]
        path = (state.get("graph_path") or "") + "→retrieve"
        return {
            "citations": payload,
            "retrieval_context": hits.context_text,
            "graph_path": path,
        }


def _route_after_retrieve(state: GraphState) -> str:
    """Branch: no hits → clarify; otherwise generate grounded answer."""
    cites = state.get("citations") or []
    return "clarify" if len(cites) == 0 else "generate"


async def _clarify(state: GraphState) -> dict:
    """Deterministic message when retrieval yields no citations (optional structured stub)."""
    with _tracer.start_as_current_span("rag.clarify"):
        libs = ", ".join(sorted(state.get("user_libraries") or ())) or "(none)"
        answer = (
            "I could not match your question to any documents in your allowed libraries "
            f"({libs}). Try rephrasing, narrowing the topic, or requesting access to the "
            "right document library."
        )
        path = (state.get("graph_path") or "") + "→clarify"
        structured = None
        if state.get("structured_output"):
            structured = {
                "summary": answer[:280],
                "suggested_checklist": ["Refine your question", "Confirm library access"],
                "risk_flag": "unknown",
            }
        return {
            "answer_text": answer,
            "structured": structured,
            "graph_path": path,
            "citations": [],
            "retrieval_context": "",
        }


def _sources_summary(state: GraphState, citations: list[Citation]) -> str:
    allowed = sorted(set(state.get("user_libraries") or ()))
    titles = ", ".join(c.title for c in citations[:5]) or "(no titles)"
    ctx = (state.get("retrieval_context") or "").strip()
    ctx_note = f" Context length: {len(ctx)} chars." if ctx else ""
    return (
        f"Sources: {titles}. Libraries: {', '.join(allowed) or '(none)'}.{ctx_note}"
    )


def _fallback_not_configured(*, state: GraphState, citations: list[Citation]) -> str:
    settings = get_settings()
    return (
        "Search found relevant documents, but no language model is configured. "
        f"{_sources_summary(state, citations)} "
        "Set OLLAMA_BASE_URL and LLM_MODEL (or LLM_BASE_URL and LLM_MODEL). "
        "With Docker Compose: run `docker compose exec ollama ollama pull llama3.2:3b` "
        "and ensure ai-core has OLLAMA_BASE_URL=http://ollama:11434. "
        f"Current: llm_backend={settings.resolved_llm_backend()}, "
        f"model={settings.llm_model or '(unset)'}, "
        f"base_url={settings.llm_base_url or '(unset)'}."
    )


def _fallback_llm_failed(
    *,
    state: GraphState,
    citations: list[Citation],
    detail: str,
) -> str:
    return (
        "Search found relevant documents, but the language model could not answer. "
        f"{_sources_summary(state, citations)} {detail}"
    )


async def _generate(state: GraphState) -> dict:
    """Call LLM with retrieval context; on empty LLM output use :func:`_fallback_stub_answer`."""
    settings = get_settings()
    with _tracer.start_as_current_span("rag.generate") as span:
        cites_raw = state.get("citations") or []
        citations = [Citation(**c) for c in cites_raw]
        user_q = state.get("message") or ""
        ctx = (state.get("retrieval_context") or "").strip()
        span.set_attribute("rag.context.length", len(ctx))
        span.set_attribute("llm.backend", settings.resolved_llm_backend())

        outcome = await generate_grounded_answer(
            user_message=user_q,
            context_text=ctx,
            settings=settings,
        )
        if outcome.text:
            answer = outcome.text
        elif outcome.not_configured:
            answer = _fallback_not_configured(state=state, citations=citations)
        else:
            answer = _fallback_llm_failed(
                state=state,
                citations=citations,
                detail=outcome.error_detail or "Unknown LLM error.",
            )
        span.set_attribute("rag.used_llm", bool(outcome.text))

        path = (state.get("graph_path") or "") + "→generate"
        structured = None
        if state.get("structured_output"):
            structured = {
                "summary": answer[:280],
                "suggested_checklist": [
                    "Confirm latest document version",
                    "Validate requester context",
                ],
                "risk_flag": "low",
            }
        return {"answer_text": answer, "structured": structured, "graph_path": path}


def _build_graph():
    """Wire state machine: retrieve → conditional → END from generate or clarify."""
    g = StateGraph(GraphState)
    g.add_node("rewrite", _rewrite)
    g.add_node("retrieve", _retrieve)
    g.add_node("clarify", _clarify)
    g.add_node("generate", _generate)
    g.set_entry_point("rewrite")
    g.add_edge("rewrite", "retrieve")
    g.add_conditional_edges(
        "retrieve",
        _route_after_retrieve,
        {"generate": "generate", "clarify": "clarify"},
    )
    g.add_edge("generate", END)
    g.add_edge("clarify", END)
    return g.compile()


class LangGraphAssistantPipeline:
    """Default :class:`~ai_search_assistant.orchestration.contracts.AssistantPipeline` implementation."""

    def __init__(self) -> None:
        self._graph = _build_graph()

    async def run(
        self, req: ChatRequest, user: UserContext, correlation_id: str
    ) -> ChatResponse:
        """Execute compiled graph and map final state to :class:`~ai_search_assistant.domain.models.ChatResponse`."""
        initial: GraphState = {
            "message": req.message,
            "structured_output": req.structured_output,
            "user_libraries": user.library_access,
        }
        final: dict | None = None
        t0 = time.perf_counter()
        with _tracer.start_as_current_span("assist.pipeline") as span:
            span.set_attribute("correlation_id", correlation_id)
            span.set_attribute(
                "user.libraries",
                ",".join(sorted(user.library_access)) if user.library_access else "",
            )
            try:
                final = await self._graph.ainvoke(initial)
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                raise
        elapsed = time.perf_counter() - t0
        path = (final or {}).get("graph_path") or "unknown"
        _pipeline_duration.record(elapsed, {"graph.path": path})
        citations = [Citation(**c) for c in (final.get("citations") or [])] if final else []
        return ChatResponse(
            correlation_id=correlation_id,
            answer_text=(final or {}).get("answer_text") or "",
            structured=(final or {}).get("structured") if final else None,
            citations=citations,
            graph_path=path,
        )


@lru_cache
def get_pipeline() -> AssistantPipeline:
    """Process-singleton pipeline (safe under fork warnings in some ASGI workers)."""
    return LangGraphAssistantPipeline()
