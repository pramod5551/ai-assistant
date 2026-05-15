"""Liveness/readiness style endpoint for orchestrators (Kubernetes, load balancers).

Kept minimal — no DB or vector checks — so the pod remains "up" even when deps are warming.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a static OK payload; extend with dependency probes if policies require it."""
    return {"status": "up"}
