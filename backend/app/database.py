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

from sqlalchemy import create_engine, inspect, text
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


def _ensure_column(table_name: str, column_name: str, column_ddl: str):
    """
    Lightweight, manual migration for exactly one situation: a table that
    ALREADY EXISTED before a new column was added to its model (e.g. adding
    user_id to the pre-existing "issues"/"documents" tables for the
    auth/privacy feature). SQLAlchemy's create_all() only creates MISSING
    tables — it never alters an existing table's columns — so without this,
    old databases would be stuck on the old schema while the Python model
    expects the new column, causing a real runtime error on every insert.

    This is a deliberately minimal substitute for a real migration tool
    (Alembic would be the production-grade choice) — appropriate for an
    academic project with one simple additive change, not a general-purpose
    migration system. It only ever ADDS a column; it never renames, drops,
    or changes an existing column's type/constraints.
    """
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return  # table doesn't exist yet — create_all() will create it fresh, already correct
    existing_columns = {c["name"] for c in inspector.get_columns(table_name)}
    if column_name in existing_columns:
        return  # already migrated
    logger.warning("init_db: migrating existing table '%s' — adding missing column '%s'",
                    table_name, column_name)
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_ddl}"))


def init_db():
    """Creates any tables that don't already exist, and migrates existing
    tables that need a new column (see _ensure_column). Safe to call on
    every app startup — never drops or modifies existing rows.

    Fail-loud by design: logs the exact resolved database path and the
    model(s) registered on Base BEFORE creating anything, then re-inspects
    the actual on-disk database afterward and raises immediately if an
    expected table isn't really there. A startup that silently "succeeds"
    without the table existing is exactly the bug this is meant to catch
    (see the Phase 5C "no such table: issues" incident).
    """
    logger.info("init_db: resolved engine URL = %s", engine.url)
    logger.info("init_db: engine.url.database (actual file path SQLAlchemy will open) = %s",
                engine.url.database)

    from app.models import issue, document, user, anonymous_usage, case  # noqa: F401  registers all models on Base.metadata

    expected_tables = {"issues", "documents", "users", "anonymous_usage", "cases"}
    registered_tables = set(Base.metadata.tables.keys())
    logger.info("init_db: tables registered on Base.metadata (Python-side, pre-create): %s",
                sorted(registered_tables))
    missing_registered = expected_tables - registered_tables
    if missing_registered:
        raise RuntimeError(
            f"init_db: {missing_registered} NOT in Base.metadata.tables even before create_all() "
            f"ran. This means a model class never got defined on the SAME Base object "
            f"database.py uses — check the model file imports Base from app.database."
        )

    # Create any brand-new tables (users, anonymous_usage, and issues/documents
    # on a truly fresh install where they don't exist yet at all).
    Base.metadata.create_all(bind=engine)

    # Migrate pre-existing issues/documents tables that predate the
    # auth/privacy feature — this is the path that actually matters for an
    # upgrade of this project's real, already-populated database.
    _ensure_column("issues", "user_id", "user_id INTEGER REFERENCES users(id)")
    _ensure_column("issues", "case_id", "case_id INTEGER REFERENCES cases(id)")
    _ensure_column("documents", "user_id", "user_id INTEGER REFERENCES users(id)")
    _ensure_column("documents", "file_retained", "file_retained BOOLEAN NOT NULL DEFAULT 0")

    # Verify against the ACTUAL file, not just Python's in-memory metadata —
    # this is the real proof create_all() + the migration did what they claimed.
    actual_tables = set(inspect(engine).get_table_names())
    logger.info("init_db: tables ACTUALLY present in the database after create_all()+migration: %s",
                sorted(actual_tables))

    missing_actual = expected_tables - actual_tables
    if missing_actual:
        raise RuntimeError(
            f"init_db: {missing_actual} still NOT present in the actual database at "
            f"{engine.url.database!r} after create_all(). Tables found: {sorted(actual_tables)}."
        )

    actual_issue_columns = {c["name"] for c in inspect(engine).get_columns("issues")}
    actual_document_columns = {c["name"] for c in inspect(engine).get_columns("documents")}
    if ("user_id" not in actual_issue_columns or "case_id" not in actual_issue_columns
            or "user_id" not in actual_document_columns):
        raise RuntimeError(
            "init_db: migration ran without raising, but 'user_id' is still missing from "
            f"issues (has: {sorted(actual_issue_columns)}) or documents "
            f"(has: {sorted(actual_document_columns)}). Ownership enforcement would silently "
            f"fail to work — refusing to start with this mismatch."
        )

    logger.info("init_db: confirmed %s all exist, with ownership columns present, in %s",
                sorted(expected_tables), engine.url.database)


def get_db():
    """FastAPI dependency: yields one session per request, always closed
    afterward (including on exceptions, via the try/finally)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
