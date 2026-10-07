"""
main.py — FastAPI application entrypoint.

Phase 5A + 5B + 5C scope: app creation, CORS, root endpoint, health router,
legal issue analysis router, and SQLite table creation on startup. Document
upload (5D) is deliberately not wired in yet.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_TITLE, API_DESCRIPTION, API_VERSION, CORS_ALLOWED_ORIGINS
from app.routers import health, issues, documents

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
app.include_router(issues.router)
app.include_router(documents.router)


@app.get("/")
def root():
    return {"message": "AI-Powered Legal Intelligence System API"}
