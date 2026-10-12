"""
main.py — FastAPI application entrypoint.

App creation, CORS (with credentials, for the anonymous-session cookie), root
endpoint, health router, auth router, legal issue router, document router, and
SQLite table creation/migration on startup.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_TITLE, API_DESCRIPTION, API_VERSION, CORS_ALLOWED_ORIGINS
from app.routers import health, issues, documents, auth, cases

# Without this, Python's default logging config suppresses INFO-level logs
# (root logger defaults to WARNING), which would hide init_db()'s path/table
# verification logging — exactly the visibility the 5C bugfix depends on.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Creates any missing tables on startup. Does NOT drop or modify
    # existing tables/rows (SQLAlchemy's create_all is a no-op for tables
    # that already exist) — safe to run on every restart.
    from app.database import init_db
    init_db()
    # Startup sweep of raw uploads that outlived their retention window.
    from app.database import SessionLocal
    from app.services import document_service
    db = SessionLocal()
    try:
        document_service.purge_stale_uploads(db)
    except Exception:
        logging.getLogger("legal_ai.main").exception("Startup purge of stale uploads failed")
    finally:
        db.close()
    yield


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(issues.router)
app.include_router(documents.router)
app.include_router(cases.router)


@app.get("/")
def root():
    return {"message": "AI-Powered Legal Intelligence System API"}
