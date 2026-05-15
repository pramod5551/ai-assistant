"""OpenTelemetry: OTLP HTTP traces + metrics, FastAPI and HTTPX auto-instrumentation."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from ai_search_assistant.config import Settings

logger = logging.getLogger(__name__)

_tracer_provider: TracerProvider | None = None
_meter_provider: MeterProvider | None = None
_httpix_instrumented: bool = False


def init_telemetry_providers(settings: Settings) -> None:
    """Configure global trace/meter providers when OTLP endpoints are set."""
    global _tracer_provider, _meter_provider, _httpix_instrumented

    traces_ep = settings.resolved_otel_traces_endpoint()
    metrics_ep = settings.resolved_otel_metrics_endpoint()

    if not traces_ep and not metrics_ep:
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
        }
    )

    if traces_ep:
        if _tracer_provider is not None:
            logger.debug("Tracer provider already configured; skipping.")
        else:
            exporter = OTLPSpanExporter(endpoint=traces_ep)
            _tracer_provider = TracerProvider(resource=resource)
            _tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(_tracer_provider)
            logger.info("OpenTelemetry tracing enabled endpoint=%s", traces_ep)

            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            if not _httpix_instrumented:
                HTTPXClientInstrumentor().instrument()
                _httpix_instrumented = True

    if metrics_ep:
        if _meter_provider is not None:
            logger.debug("Meter provider already configured; skipping.")
        else:
            metric_exporter = OTLPMetricExporter(endpoint=metrics_ep)
            reader = PeriodicExportingMetricReader(
                metric_exporter,
                export_interval_millis=settings.otel_metric_export_interval_ms,
            )
            _meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
            metrics.set_meter_provider(_meter_provider)
            logger.info("OpenTelemetry metrics enabled endpoint=%s", metrics_ep)


def instrument_fastapi_app(app: FastAPI, settings: Settings) -> None:
    """Attach FastAPI auto-instrumentation when traces endpoint is configured (skips health/docs)."""
    if not settings.resolved_otel_traces_endpoint():
        return
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/docs,/openapi.json,/redoc",
    )


def shutdown_telemetry_providers() -> None:
    """Flush and tear down SDK providers on process shutdown (best-effort logging on failure)."""
    global _tracer_provider, _meter_provider
    if _tracer_provider is not None:
        try:
            _tracer_provider.shutdown()
        except Exception:
            logger.exception("Tracer provider shutdown failed")
        _tracer_provider = None
    if _meter_provider is not None:
        try:
            _meter_provider.shutdown()
        except Exception:
            logger.exception("Meter provider shutdown failed")
        _meter_provider = None
