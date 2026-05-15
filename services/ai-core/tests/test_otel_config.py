import pytest


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    from ai_assistant.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_otel_endpoints_from_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
    from ai_assistant.config import get_settings

    s = get_settings()
    assert s.resolved_otel_traces_endpoint() == "http://otel-collector:4318/v1/traces"
    assert s.resolved_otel_metrics_endpoint() == "http://otel-collector:4318/v1/metrics"


def test_otel_disabled_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel:4318")
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    from ai_assistant.config import get_settings

    s = get_settings()
    assert s.resolved_otel_traces_endpoint() is None
    assert s.resolved_otel_metrics_endpoint() is None


def test_otel_explicit_trace_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        "http://custom:4318/v1/traces",
    )
    from ai_assistant.config import get_settings

    s = get_settings()
    assert s.resolved_otel_traces_endpoint() == "http://custom:4318/v1/traces"
