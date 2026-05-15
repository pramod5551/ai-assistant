"""HTTP client for OpenAI-compatible ``/embeddings`` endpoints (remote or sidecar)."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class OpenAICompatibleEmbedder:
    """Remote embeddings via POST {api_base}/embeddings (OpenAI, vLLM embed, etc.)."""

    def __init__(
        self,
        api_base: str,
        model: str,
        api_key: str | None = None,
        timeout_seconds: float = 120.0,
    ) -> None:
        self._base = api_base.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """POST embeddings; reorder vectors by ``index`` so output aligns with ``texts``."""
        if not texts:
            return []
        url = f"{self._base}/embeddings"
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {"model": self._model, "input": texts}
        try:
            t = float(self._timeout)
            timeout = httpx.Timeout(connect=15.0, read=t, write=t, pool=30.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                body = resp.json()
        except Exception:
            logger.exception("Embedding HTTP request failed url=%s", url)
            raise

        data = body.get("data") or []
        if len(data) != len(texts):
            raise ValueError(
                f"Embedding API returned {len(data)} vectors for {len(texts)} inputs"
            )
        indexed: dict[int, list[float]] = {}
        for item in data:
            idx = int(item.get("index", len(indexed)))
            emb = item.get("embedding")
            if not isinstance(emb, list):
                raise ValueError("Invalid embedding item in API response")
            indexed[idx] = [float(x) for x in emb]
        return [indexed[i] for i in range(len(texts))]
