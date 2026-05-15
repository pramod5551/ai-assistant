"""Central configuration: environment variables, validation, and resolved backend choices.

Settings are loaded via Pydantic ``BaseSettings`` (``.env`` + process env). Application code
should call :func:`get_settings` once per process (cached) and use ``resolved_*`` methods
instead of re-implementing ``auto`` logic.

**Extending:** add a field, optional validators, and a ``resolved_*`` helper; then branch in
``main.py`` (lifespan), ``search/runtime.py`` (retrieval), or embedding/LLM factories.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Literal, Self

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from qdrant_client.models import Distance

AuditBackend = Literal["auto", "none", "sql"]
VectorBackend = Literal["auto", "stub", "qdrant"]
EmbeddingBackend = Literal["auto", "fastembed", "openai_compatible"]
LlmBackend = Literal["auto", "none", "http"]
QdrantDistance = Literal["cosine", "euclid", "dot", "manhattan"]


class Settings(BaseSettings):
    """
    All integration points are environment-driven.

    **Audit / DB:** set ``DATABASE_URL`` to any SQLAlchemy **async** URL after installing the
    matching driver (``asyncpg``, ``aiosqlite``, ``aiomysql``, …).

    **LLM:** OpenAI-compatible HTTP (OpenAI, Azure OpenAI via base URL, vLLM, LM Studio,
    Ollama ``/v1``, etc.). Set ``LLM_BASE_URL`` + ``LLM_MODEL``, or only ``OLLAMA_BASE_URL``.

    **Embeddings:** local FastEmbed or OpenAI-compatible ``/v1/embeddings``.

    **Vectors:** in-process stub or Qdrant (plug-in pattern for other stores in code).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "ai-assistant-core"
    internal_token: str = Field(
        default="dev-internal-token",
        validation_alias=AliasChoices("INTERNAL_TOKEN", "internal_token"),
    )
    cors_origins: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"),
    )

    # --- Audit / operational DB (any SQLAlchemy async URL) ---
    audit_backend: AuditBackend = "auto"
    database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "SQLALCHEMY_DATABASE_URI",
            "AUDIT_DATABASE_URL",
            "database_url",
        ),
        description="Async SQLAlchemy URL, e.g. postgresql+asyncpg://... or sqlite+aiosqlite:///...",
    )

    # --- Vector store ---
    vector_backend: VectorBackend = "auto"
    qdrant_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("QDRANT_URL", "qdrant_url", "VECTOR_DATABASE_URL"),
    )
    vector_collection: str = Field(
        default="assistant_chunks",
        validation_alias=AliasChoices(
            "VECTOR_COLLECTION",
            "QDRANT_COLLECTION",
            "vector_collection",
        ),
    )
    qdrant_distance: QdrantDistance = Field(
        default="cosine",
        validation_alias=AliasChoices("QDRANT_DISTANCE", "qdrant_distance"),
    )
    seed_vector_collection_on_startup: bool = Field(
        default=True,
        description="If true, upsert demo chunks when the vector collection is empty.",
        validation_alias=AliasChoices(
            "SEED_VECTOR_COLLECTION_ON_STARTUP",
            "SEED_QDRANT_ON_STARTUP",
        ),
    )
    vector_search_limit: int = Field(
        default=20,
        ge=1,
        le=100,
        validation_alias=AliasChoices("VECTOR_SEARCH_LIMIT", "vector_search_limit"),
    )

    # --- Embeddings ---
    embedding_backend: EmbeddingBackend = "auto"
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        validation_alias=AliasChoices(
            "EMBED_MODEL",
            "EMBEDDING_MODEL",
            "embedding_model",
        ),
    )
    embedding_api_base: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "EMBEDDING_API_BASE",
            "OPENAI_API_BASE",
            "VLLM_EMBEDDING_BASE",
            "embedding_api_base",
        ),
        description="OpenAI-compatible base URL including /v1",
    )
    embedding_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("EMBEDDING_API_KEY", "OPENAI_API_KEY"),
    )
    embedding_request_timeout_seconds: float = Field(
        default=120.0,
        validation_alias=AliasChoices(
            "EMBEDDING_REQUEST_TIMEOUT_SECONDS",
            "embedding_request_timeout_seconds",
        ),
    )

    # --- LLM (OpenAI-compatible chat — works with OpenAI, vLLM, Ollama, LM Studio, etc.) ---
    llm_backend: LlmBackend = "auto"
    llm_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LLM_BASE_URL",
            "OPENAI_BASE_URL",
            "VLLM_BASE_URL",
            "LM_STUDIO_BASE_URL",
            "llm_base_url",
        ),
        description="OpenAI-compatible API root including /v1 (e.g. https://api.openai.com/v1 or http://ollama:11434/v1).",
    )

    ollama_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OLLAMA_BASE_URL",
            "OLLAMA_HOST",
            "ollama_base_url",
        ),
        description="If LLM_BASE_URL is unset, derived as {OLLAMA_BASE_URL}/v1 (adds http:// if missing).",
    )
    llm_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_MODEL", "OPENAI_MODEL", "OLLAMA_MODEL", "llm_model"),
    )
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LLM_API_KEY",
            "AZURE_OPENAI_API_KEY",
            "OPENAI_CHAT_API_KEY",
            "llm_api_key",
        ),
    )
    llm_request_timeout_seconds: float = Field(
        default=120.0,
        ge=5.0,
        le=600.0,
        validation_alias=AliasChoices(
            "LLM_REQUEST_TIMEOUT_SECONDS",
            "llm_request_timeout_seconds",
        ),
    )

    # --- OpenTelemetry (OTLP over HTTP/protobuf) ---
    otel_sdk_disabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("OTEL_SDK_DISABLED", "otel_sdk_disabled"),
        description="If true, do not configure OTLP exporters.",
    )
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "otel_exporter_otlp_endpoint",
        ),
        description="OTLP HTTP base URL, e.g. http://otel-collector:4318 (appends /v1/traces).",
    )
    otel_exporter_otlp_traces_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
            "otel_exporter_otlp_traces_endpoint",
        ),
    )
    otel_exporter_otlp_metrics_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
            "otel_exporter_otlp_metrics_endpoint",
        ),
    )
    otel_service_name: str = Field(
        default="ai-assistant-core",
        validation_alias=AliasChoices("OTEL_SERVICE_NAME", "otel_service_name"),
    )
    otel_metric_export_interval_ms: int = Field(
        default=10_000,
        ge=1_000,
        le=300_000,
        validation_alias=AliasChoices(
            "OTEL_METRIC_EXPORT_INTERVAL_MS",
            "otel_metric_export_interval_ms",
        ),
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, v: object) -> object:
        if v is None or v == "":
            return []
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    @field_validator("audit_backend", mode="before")
    @classmethod
    def normalize_audit_backend(cls, v: object) -> object:
        if isinstance(v, str):
            lo = v.strip().lower()
            if lo in ("postgres", "postgresql", "mysql", "sqlite"):
                return "sql"
            return lo
        return v

    @field_validator("otel_sdk_disabled", mode="before")
    @classmethod
    def normalize_otel_sdk_disabled(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "on")
        return v

    @field_validator("qdrant_distance", mode="before")
    @classmethod
    def normalize_distance(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower()
        return v

    @model_validator(mode="after")
    def derive_llm_base_from_ollama(self) -> Self:
        if self.llm_base_url is None and self.ollama_base_url:
            raw = self.ollama_base_url.strip()
            if not raw.startswith("http://") and not raw.startswith("https://"):
                raw = f"http://{raw}"
            base = raw.rstrip("/")
            # Ollama OpenAI compatibility lives under /v1
            object.__setattr__(self, "llm_base_url", f"{base}/v1")
        return self

    def resolved_audit_backend(self) -> Literal["none", "sql"]:
        if self.audit_backend == "auto":
            return "sql" if self.database_url else "none"
        if self.audit_backend == "sql":
            if not self.database_url:
                raise ValueError(
                    "audit_backend=sql requires DATABASE_URL (or an alias) to be set."
                )
            return "sql"
        return "none"

    def resolved_vector_backend(self) -> Literal["stub", "qdrant"]:
        if self.vector_backend == "auto":
            return "qdrant" if self.qdrant_url else "stub"
        if self.vector_backend == "qdrant":
            if not self.qdrant_url:
                raise ValueError("vector_backend=qdrant requires QDRANT_URL.")
            return "qdrant"
        return "stub"

    def resolved_embedding_backend(self) -> Literal["fastembed", "openai_compatible"]:
        if self.resolved_vector_backend() == "stub":
            return "fastembed"
        eb = self.embedding_backend
        if eb == "auto":
            return "openai_compatible" if self.embedding_api_base else "fastembed"
        if eb == "openai_compatible":
            if not self.embedding_api_base:
                raise ValueError(
                    "embedding_backend=openai_compatible requires EMBEDDING_API_BASE "
                    "(or OPENAI_API_BASE, etc.)."
                )
            return "openai_compatible"
        return "fastembed"

    def resolved_llm_backend(self) -> Literal["none", "http"]:
        if self.llm_backend == "auto":
            return "http" if (self.llm_base_url and self.llm_model) else "none"
        if self.llm_backend == "http":
            if not (self.llm_base_url and self.llm_model):
                raise ValueError(
                    "llm_backend=http requires LLM_BASE_URL (or OLLAMA_BASE_URL) and LLM_MODEL."
                )
            return "http"
        return "none"

    def qdrant_distance_metric(self) -> Distance:
        from qdrant_client.models import Distance

        mapping: dict[str, Distance] = {
            "cosine": Distance.COSINE,
            "euclid": Distance.EUCLID,
            "dot": Distance.DOT,
            "manhattan": Distance.MANHATTAN,
        }
        key = self.qdrant_distance.lower()
        if key not in mapping:
            raise ValueError(f"Invalid qdrant_distance={self.qdrant_distance!r}")
        return mapping[key]

    def resolved_otel_traces_endpoint(self) -> str | None:
        if self.otel_sdk_disabled:
            return None
        if self.otel_exporter_otlp_traces_endpoint:
            return _otlp_join(self.otel_exporter_otlp_traces_endpoint, "/v1/traces")
        if self.otel_exporter_otlp_endpoint:
            return _otlp_join(self.otel_exporter_otlp_endpoint, "/v1/traces")
        return None

    def resolved_otel_metrics_endpoint(self) -> str | None:
        if self.otel_sdk_disabled:
            return None
        if self.otel_exporter_otlp_metrics_endpoint:
            return _otlp_join(self.otel_exporter_otlp_metrics_endpoint, "/v1/metrics")
        if self.otel_exporter_otlp_endpoint:
            return _otlp_join(self.otel_exporter_otlp_endpoint, "/v1/metrics")
        return None


def _otlp_join(base_or_full: str, path_suffix: str) -> str:
    """Append OTLP path (``/v1/traces`` etc.) if ``base_or_full`` is collector root without suffix."""
    u = base_or_full.strip().rstrip("/")
    if u.endswith(path_suffix):
        return u
    return f"{u}{path_suffix}"


@lru_cache
def get_settings() -> Settings:
    """Return process-wide settings instance (read once from env / ``.env`` via Pydantic)."""
    return Settings()


def reset_settings_cache() -> None:
    """For tests only — forces re-read of environment."""
    get_settings.cache_clear()
