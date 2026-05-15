# ---------- build: install deps into a venv (not copied to runtime as a build layer) ----------
FROM python:3.12-slim-bookworm AS builder
WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY ai_search_assistant ./ai_search_assistant

# ---------- runtime: slim Python only (FastEmbed/ONNX need libstdc++ etc.; Distroless Python lacks these) ----------
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"
# FastEmbed / HuggingFace caches when running as non-root
ENV HOME=/tmp
ENV HF_HOME=/tmp/hf
ENV FASTEMBED_CACHE_PATH=/tmp/fastembed

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /build/ai_search_assistant ./ai_search_assistant

# Legacy .doc extraction (soffice); antiword as fallback.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui \
        antiword \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /tmp/hf /tmp/fastembed && chown -R nobody:nogroup /tmp/hf /tmp/fastembed

USER nobody
EXPOSE 8081
CMD ["uvicorn", "ai_search_assistant.main:app", "--host", "0.0.0.0", "--port", "8081"]
