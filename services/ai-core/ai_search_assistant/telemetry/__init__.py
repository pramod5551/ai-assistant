"""Re-export telemetry helpers for ``from ai_search_assistant.telemetry import ...``."""

from ai_search_assistant.telemetry.setup import (
    init_telemetry_providers,
    instrument_fastapi_app,
    shutdown_telemetry_providers,
)

__all__ = [
    "init_telemetry_providers",
    "instrument_fastapi_app",
    "shutdown_telemetry_providers",
]
