"""
config.py — central configuration + the one piece of plumbing Phase 5 needs
that didn't exist before: making the existing root-level RAG modules
(rag_engine.py, issue_analyzer.py, llm_client.py) importable from inside the
backend package, WITHOUT moving, duplicating, or modifying them.

Project layout (unchanged from Phase 1-4):

    legal_rag_project/                  <- PROJECT_ROOT (this is where
    |                                       rag_engine.py etc. actually live)
    |-- rag_engine.py
    |-- issue_analyzer.py
    |-- llm_client.py
    |-- indian_legal_acts_master.json
    |-- case_law_master.json
    |-- chroma_laws/  chroma_cases/
    |-- bm25_laws.pkl  bm25_cases.pkl
    |-- .env
    `-- backend/
        `-- app/
            |-- config.py                <- you are here
            |-- main.py
            `-- ...

issue_analyzer.py does `from rag_engine import ...` and `from llm_client import
...` — plain top-level imports that assume both files sit in the same
directory on sys.path. The cleanest minimal fix is exactly that: add
PROJECT_ROOT to sys.path, once, before anything tries to import those
modules. No relocation, no duplication, no changes to the RAG files
themselves.
"""

import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# backend/app/config.py -> backend/app -> backend -> legal_rag_project
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env from the project root (where the existing Phase 4 .env already
# lives) so GROQ_API_KEY etc. are available to llm_client.py exactly as
# before — we do NOT require a second .env inside backend/.
load_dotenv(PROJECT_ROOT / ".env")

API_TITLE = "AI-Powered Legal Intelligence System"
API_DESCRIPTION = (
    "Backend API wrapping the existing Phase 3/4 hybrid RAG legal-analysis "
    "engine (Chroma + BM25 + Groq). Informational only — not legal advice."
)
API_VERSION = "0.5.0"  # Phase 5

# CORS — allow Vite React dev server and production deployments.
_cors_env = os.environ.get("CORS_ALLOWED_ORIGINS")
if _cors_env:
    CORS_ALLOWED_ORIGINS = [orig.strip() for orig in _cors_env.split(",") if orig.strip()]
else:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

# .as_posix() is deliberate, not cosmetic: on Windows, Path.__str__ uses
# backslashes (C:\Users\...\backend\legal_ai.db), which produces a BROKEN
# SQLAlchemy sqlite:/// URL if interpolated directly. .as_posix() gives
# forward slashes (C:/Users/.../backend/legal_ai.db), which combined with
# the three slashes below yields the correct absolute-path form SQLAlchemy
# expects: sqlite:///C:/Users/.../backend/legal_ai.db
DATABASE_URL = os.environ.get(
    "DATABASE_URL", f"sqlite:///{(BACKEND_ROOT / 'legal_ai.db').as_posix()}"
)

UPLOAD_DIR = BACKEND_ROOT / "uploads"
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}

# ---------------- Authentication (added for the privacy/auth feature) ----------------
import secrets as _secrets  # local import, only used for the dev-fallback secret below

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    # No hardcoded fallback secret — a guessable default committed to source
    # would defeat the point of signing tokens at all. Instead, generate a
    # random secret for THIS PROCESS only and warn loudly. Consequence:
    # every existing token becomes invalid on restart (everyone has to log
    # in again) — an acceptable, SAFE failure mode for an academic project,
    # unlike silently accepting a weak default secret would be.
    JWT_SECRET_KEY = _secrets.token_hex(32)
    logging.getLogger("legal_ai.config").warning(
        "JWT_SECRET_KEY not set in .env — generated a random one for this process only. "
        "Existing tokens will NOT survive a server restart. Set JWT_SECRET_KEY in your "
        "project-root .env for stable sessions across restarts."
    )

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))

# Anonymous one-time-use session cookie (backend-enforced, not React state).
ANON_SESSION_COOKIE_NAME = "anon_session_id"
ANON_SESSION_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365  # 1 year — "one ever," not "one per day"

# Raw uploaded files are deleted as soon as analysis runs. An upload that is
# NEVER analyzed (tab closed, request failed before analyze) would otherwise
# sit on disk forever, so anything older than this is purged — at server
# startup and at the start of every upload. See document_service.purge_stale_uploads.
UPLOAD_TTL_MINUTES = int(os.environ.get("UPLOAD_TTL_MINUTES", "60"))
