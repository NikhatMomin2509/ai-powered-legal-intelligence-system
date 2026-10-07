"""
database.py — SQLAlchemy engine/session setup for SQLite persistence
(Phase 5C). This is purely infrastructure: it knows nothing about issues,
documents, or any domain logic — models/issue.py defines what gets stored.

Bugfix note (post-Phase-5C): the original init_db() called
Base.metadata.create_all() and trusted it silently — no path logging, no
verification that a table actually landed on disk. That's not good enough:
Base.metadata.tables being populated only proves the Python MODEL
registered; it says nothing about whether SQLite actually wrote the table
to the file on disk. init_db() now logs the exact resolved path and
re-inspects the ACTUAL database file afterward, and raises loudly if the
expected table isn't really there — matching "do not silently swallow
database initialization errors."
"""

import logging

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

logger = logging.getLogger("legal_ai.database")

# check_same_thread=False: FastAPI's sync (def, not async def) endpoints run
# in a threadpool, so a single SQLite connection can be touched from more
# than one thread across the app's lifetime. This disables sqlite3's own
# same-thread guard; SQLAlchemy's connection handling still keeps actual
# access safe for SQLite's single-writer model. This is the standard,
# minimal FastAPI+SQLite setting — not a workaround for anything unusual
# here.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Creates any tables that don't already exist. Safe to call on every
    app startup — SQLAlchemy's create_all() is a no-op for tables that
    already exist, and never drops or modifies existing rows/tables.

    Fail-loud by design: logs the exact resolved database path and the
    model(s) registered on Base BEFORE creating anything, then re-inspects
    the actual on-disk database afterward and raises immediately if the
    expected table isn't really there. A startup that silently "succeeds"
    without the table existing is exactly the bug this is meant to catch.
    """
    logger.info("init_db: resolved engine URL = %s", engine.url)
    logger.info("init_db: engine.url.database (actual file path SQLAlchemy will open) = %s",
                engine.url.database)

    from app.models import issue, document  # noqa: F401  (registers both models on Base.metadata)

    expected_tables = {"issues", "documents"}
    registered_tables = set(Base.metadata.tables.keys())
    logger.info("init_db: tables registered on Base.metadata (Python-side, pre-create): %s",
                sorted(registered_tables))
    missing_registered = expected_tables - registered_tables
    if missing_registered:
        raise RuntimeError(
            f"init_db: {missing_registered} NOT in Base.metadata.tables even before create_all() "
            f"ran. This means the model class never got defined on the SAME Base object "
            f"database.py uses — check the model file imports Base from app.database."
        )

    Base.metadata.create_all(bind=engine)

    # Verify against the ACTUAL file, not just Python's in-memory metadata —
    # this is the real proof create_all() did what it claimed.
    actual_tables = set(inspect(engine).get_table_names())
    logger.info("init_db: tables ACTUALLY present in the database after create_all(): %s",
                sorted(actual_tables))

    missing_actual = expected_tables - actual_tables
    if missing_actual:
        raise RuntimeError(
            f"init_db: create_all() ran without raising, but {missing_actual} still NOT present "
            f"in the actual database at {engine.url.database!r}. Tables found: {sorted(actual_tables)}. "
            f"This should not be possible — if you see this, check file permissions on that "
            f"path, and whether it sits in a cloud-synced folder (OneDrive/Dropbox) that could "
            f"be interfering with the file."
        )

    logger.info("init_db: confirmed %s all exist in %s", sorted(expected_tables), engine.url.database)


def get_db():
    """FastAPI dependency: yields one session per request, always closed
    afterward (including on exceptions, via the try/finally)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
