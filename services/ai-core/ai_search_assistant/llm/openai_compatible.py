"""OpenAI-compatible chat completions (Ollama, vLLM, OpenAI, etc.)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from ai_search_assistant.config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an internal assistant. Answer ONLY using the CONTEXT blocks below. "
    "If the answer is not in the context, say you do not have enough grounded information "
    "and avoid guessing. If context is ambiguous or contradictory, say so briefly. "
    "Do not invent document ids or citations that do not appear in CONTEXT. "
    "Be concise. When you state a fact from a passage, add the document_id in parentheses "
    "as shown in the bracketed headers (e.g. document_id from [doc-id] lines)."
)


@dataclass(frozen=True)
class LlmOutcome:
    """Result of a grounded chat completion attempt."""

    text: str | None = None
    """Assistant message when the LLM call succeeded."""

    not_configured: bool = False
    """True when LLM_BASE_URL / LLM_MODEL (or OLLAMA_BASE_URL) are missing."""

    error_detail: str | None = None
    """Set when configured but the HTTP call failed or returned empty content."""


async def generate_grounded_answer(
    *,
    user_message: str,
    context_text: str,
    settings: Settings,
) -> LlmOutcome:
    """Call ``/chat/completions`` with retrieval context; return text or a failure reason."""
    if settings.resolved_llm_backend() == "none":
        return LlmOutcome(not_configured=True)
    base = settings.llm_base_url
    model = settings.llm_model
    if not base or not model:
        return LlmOutcome(not_configured=True)
    base = base.rstrip("/")
    url = f"{base}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"

    body = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"CONTEXT:\n{context_text}\n\nQUESTION:\n{user_message}",
            },
        ],
    }
    read_s = float(settings.llm_request_timeout_seconds)
    timeout = httpx.Timeout(connect=15.0, read=read_s, write=read_s, pool=30.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            logger.warning("LLM returned no choices: %s", data)
            return LlmOutcome(
                error_detail="The language model returned an empty response.",
            )
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return LlmOutcome(text=content.strip())
        return LlmOutcome(
            error_detail="The language model returned an empty message.",
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        body_preview = ""
        try:
            body_preview = exc.response.text[:300]
        except Exception:
            pass
        logger.warning(
            "LLM HTTP error status=%s url=%s body=%s",
            status,
            url,
            body_preview,
        )
        if status == 404:
            return LlmOutcome(
                error_detail=(
                    f"Model {model!r} was not found at {base}. "
                    "Pull it in Ollama, e.g. docker compose exec ollama ollama pull "
                    f"{model}"
                ),
            )
        return LlmOutcome(
            error_detail=f"Language model HTTP {status} at {base} (model {model!r}).",
        )
    except httpx.ConnectError:
        logger.exception("LLM connection failed url=%s", url)
        return LlmOutcome(
            error_detail=(
                f"Cannot reach the language model at {base}. "
                "Is Ollama running? For Docker: docker compose up -d ollama"
            ),
        )
    except httpx.TimeoutException:
        logger.exception("LLM request timed out url=%s", url)
        return LlmOutcome(
            error_detail=(
                "The language model timed out. Try a shorter question or a smaller model "
                f"(current: {model!r})."
            ),
        )
    except Exception as exc:
        logger.exception("LLM request failed url=%s", url)
        return LlmOutcome(error_detail=f"Language model error: {exc}")


# Backward-compatible helper for callers expecting str | None
async def generate_grounded_answer_text(
    *,
    user_message: str,
    context_text: str,
    settings: Settings,
) -> str | None:
    outcome = await generate_grounded_answer(
        user_message=user_message,
        context_text=context_text,
        settings=settings,
    )
    return outcome.text
