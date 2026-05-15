"""SQLAlchemy ORM base and metadata registration for audit storage.

Audit rows live in models under this package; engines are created in :mod:`ai_search_assistant.persistence.db`.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM tables (single metadata registry)."""

    pass
