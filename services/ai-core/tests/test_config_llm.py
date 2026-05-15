import pytest


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    from ai_search_assistant.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_ollama_base_derives_llm_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("LLM_MODEL", "llama3.2")
    from ai_search_assistant.config import get_settings

    s = get_settings()
    assert s.llm_base_url == "http://localhost:11434/v1"
    assert s.resolved_llm_backend() == "http"


def test_ollama_host_adds_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:11434")
    monkeypatch.setenv("LLM_MODEL", "x")
    from ai_search_assistant.config import get_settings

    s = get_settings()
    assert s.llm_base_url == "http://127.0.0.1:11434/v1"


def test_audit_postgres_alias_to_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUDIT_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@h/d")
    from ai_search_assistant.config import get_settings

    s = get_settings()
    assert s.audit_backend == "sql"
    assert s.resolved_audit_backend() == "sql"
