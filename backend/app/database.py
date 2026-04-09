"""
backend.app.database
====================
Database engine and session helpers.

Configuration
-------------
DATABASE_URL    SQLAlchemy-compatible URL.  Examples:
                  postgresql+psycopg2://user:pass@host/db
                  sqlite:///./dev.db
                  sqlite:///:memory:   (tests)

When DATABASE_URL is not set the module still imports cleanly but
``get_engine()`` / ``get_session()`` raise ``RuntimeError`` with a
helpful message so the calling route can return HTTP 503.

Call ``init_db()`` once at application start-up to create all tables
(no-op if the tables already exist).
"""

from __future__ import annotations

import os
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

_engine = None


def get_engine():
    """Return (and lazily create) the shared SQLAlchemy engine."""
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL", "").strip()
        if not url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. "
                "Configure a Postgres (or SQLite) URL to enable folder persistence."
            )
        # connect_args only needed for SQLite
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
    return _engine


def reset_engine(url: str | None = None) -> None:
    """Replace the cached engine – used in tests to inject a fresh SQLite URL."""
    global _engine
    _engine = None
    if url is not None:
        os.environ["DATABASE_URL"] = url


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency – yields a DB session per request."""
    with Session(get_engine()) as session:
        yield session


def init_db() -> None:
    """Create all tables defined in ``backend.app.models`` (idempotent)."""
    from backend.app import models as _models  # noqa: F401 – registers SQLModel metadata

    SQLModel.metadata.create_all(get_engine())
