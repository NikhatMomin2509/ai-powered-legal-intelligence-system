"""
routers/issues.py — POST /api/issues/analyze

Validation is handled entirely by IssueAnalysisRequest (Pydantic) — FastAPI
returns HTTP 422 automatically for anything that fails it (empty,
whitespace-only, under MIN_QUERY_LENGTH). This router's own try/except only
has to handle failures from the analyzer itself.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

# Import app.config first to guarantee the sys.path bootstrap has run before
# importing root-level RAG modules directly (see config.py's docstring).
from app import config  # noqa: F401

from app.database import get_db
from app.models.issue import IssueAnalysis
from app.schemas.issue import IssueAnalysisRequest, IssueAnalysisResponse
from app.services.issue_service import analyze_issue

from llm_client import LLMConfigError, LLMTruncatedError
from rag_engine import RAGEngineError

logger = logging.getLogger("legal_ai.issues")

router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.post("/analyze", response_model=IssueAnalysisResponse)
def analyze(request: IssueAnalysisRequest, db: Session = Depends(get_db)):
    try:
        return analyze_issue(request.query, db)

    except RAGEngineError as e:
        # Missing/empty Chroma or BM25 index — an infrastructure problem,
        # not something caused by this particular request.
        logger.error("RAG engine unavailable: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Legal analysis could not be completed: the retrieval system is unavailable.",
        )

    except LLMConfigError as e:
        # Missing/invalid GROQ_API_KEY. Message is logged server-side only —
        # never forwarded to the client, so the key's absence/value can't leak.
        logger.error("LLM configuration error: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Legal analysis could not be completed: the language model is not configured.",
        )

    except LLMTruncatedError as e:
        logger.error("LLM response truncated: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Legal analysis could not be completed: the response was too long to process. "
                   "Please try a shorter or simpler query.",
        )

    except ValueError as e:
        # Covers issue_analyzer._extract_json()'s "no valid JSON found" case —
        # a malformed LLM response, not a request-validation problem (that's
        # already handled by Pydantic before we get here).
        logger.error("Analyzer output could not be parsed: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Legal analysis could not be completed due to an internal processing error.",
        )

    except Exception:
        # Catch-all: never leak a raw stack trace or exception message to the client.
        logger.exception("Unexpected error during legal issue analysis")
        raise HTTPException(status_code=500, detail="Legal analysis could not be completed.")


@router.get("")
def list_issues(db: Session = Depends(get_db)):
    """History list — deliberately lightweight (id/query/issue_type/created_at
    only), not the full RAG output, per the Phase 5C spec. Fetch
    GET /api/issues/{id} for the complete saved analysis.

    Bugfix note: this previously had NO error handling at all — a database
    problem (e.g. the "no such table: issues" bug) would leak a raw
    SQLAlchemy traceback straight to the client. Now matches the same
    "never leak internals" standard as POST /analyze.
    """
    try:
        rows = (
            db.query(IssueAnalysis)
            .order_by(IssueAnalysis.created_at.desc())
            .all()
        )
        return [
            {
                "id": row.id,
                "query": row.query,
                "issue_type": row.issue_type,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    except Exception:
        logger.exception("Database error while listing issue analyses")
        raise HTTPException(status_code=500, detail="Could not retrieve issue history.")


@router.get("/{issue_id}")
def get_issue(issue_id: int, db: Session = Depends(get_db)):
    try:
        row = db.query(IssueAnalysis).filter(IssueAnalysis.id == issue_id).first()
    except Exception:
        logger.exception("Database error while fetching issue analysis id=%s", issue_id)
        raise HTTPException(status_code=500, detail="Could not retrieve the requested issue analysis.")

    if row is None:
        raise HTTPException(status_code=404, detail="Issue analysis not found.")

    # full_result is the complete, verbatim analyzer output; id/query/created_at
    # are added on top since full_result alone doesn't carry the DB identity.
    return {
        "id": row.id,
        "query": row.query,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        **(row.full_result or {}),
    }
