"""FastAPI dependency injectors for internal (BFF-only) routes.

These enforce the shared-secret internal token and map trust headers into :class:`UserContext`.
They assume the edge BFF has already authenticated the end user (OIDC, etc.).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from ai_search_assistant.config import Settings, get_settings
from ai_search_assistant.domain.models import UserContext


def get_correlation_id(request: Request) -> str:
    """Return correlation id set by :class:`ai_search_assistant.middleware.correlation.CorrelationIdMiddleware`."""
    return getattr(request.state, "correlation_id", "unknown")


InternalToken = Annotated[str | None, Header(alias="X-Internal-Token")]
UserSub = Annotated[str | None, Header(alias="X-User-Sub")]
UserRoles = Annotated[str | None, Header(alias="X-User-Roles")]
LibraryAccess = Annotated[str | None, Header(alias="X-User-Library-Access")]


def require_internal_token(
    settings: Annotated[Settings, Depends(get_settings)],
    token: InternalToken,
) -> None:
    """Reject requests that do not present the configured shared secret (``INTERNAL_TOKEN``)."""
    if token != settings.internal_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal token",
        )


def get_user_context(
    sub: UserSub,
    roles_header: UserRoles,
    libraries_header: LibraryAccess,
) -> UserContext:
    """Parse comma-separated trust headers into a structured :class:`UserContext`.

    Raises:
        HTTPException: If ``X-User-Sub`` is missing — the BFF must always identify the user.
    """
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Sub",
        )
    roles = tuple(r.strip() for r in (roles_header or "").split(",") if r.strip())
    libs = tuple(lib.strip() for lib in (libraries_header or "").split(",") if lib.strip())
    return UserContext(subject=sub, roles=roles, library_access=libs)
