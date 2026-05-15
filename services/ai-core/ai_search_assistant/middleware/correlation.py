"""HTTP middleware that propagates or generates ``X-Correlation-Id`` end-to-end.

Ensures logs and traces can be joined across the BFF hop without requiring W3C trace context.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Populate ``request.state.correlation_id`` and echo the header on responses."""

    #: Header name agreed with the Spring BFF and other ingress proxies.
    header_name = "X-Correlation-Id"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Use inbound id if present; otherwise assign a new UUID."""
        cid = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.correlation_id = cid
        response = await call_next(request)
        response.headers[self.header_name] = cid
        return response
