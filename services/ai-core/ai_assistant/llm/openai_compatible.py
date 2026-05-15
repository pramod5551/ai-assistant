"""OpenAI-compatible chat completions (Ollama, vLLM, OpenAI, etc.)."""

from __future__ import annotations

import logging

import httpx

from ai_assistant.config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an internal assistant. Answer ONLY using the CONTEXT blocks below. "
    "If the answer is not in the context, say you do not have enough grounded information "
    "and avoid guessing. If context is ambiguous or contradictory, say so briefly. "
    "Do not invent document ids or citations that do not appear in CONTEXT. "
    "Be concise. When you state a fact from a passage, add the document_id in parentheses "
    "as shown in the bracketed headers (e.g. document_id from [doc-id] lines)."
)


async def generate_grounded_answer(
    *,
    user_message: str,
    context_text: str,
    settings: Settings,
) -> str | None:
    """Return assistant text from ``/chat/completions``, or ``None`` if LLM disabled / misconfigured / error.

    The system prompt constrains answers to ``context_text`` to reduce hallucination relative to retrieval.
    """
    if settings.resolved_llm_backend() == "none":
        return None
    base = settings.llm_base_url
    model = settings.llm_model
    if not base or not model:
        return None
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
            return None
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        return None
    except Exception:
        logger.exception("LLM request failed")
        return None
