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

# CORS — allow the future Vite React dev server. Kept as an explicit list
# (not "*") so it's easy to see and extend later without surprises.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BACKEND_ROOT / 'legal_ai.db'}")

UPLOAD_DIR = BACKEND_ROOT / "uploads"
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
