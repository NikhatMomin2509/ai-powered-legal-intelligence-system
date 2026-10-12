"""
routers/issues.py — POST /api/issues/analyze (public, one-time anonymous
allowance, backend-enforced), GET /api/issues and GET /api/issues/{id}
(require authentication, strictly owner-filtered).

ANONYMOUS ALLOWANCE DESIGN (read this before touching the logic below):
- Identified by a server-set, httpOnly, SameSite=Lax cookie (anon_session_id)
  — not a value the frontend ever reads or sends itself, and not something
  React state tracks. A user cannot bypass this by refreshing the page,
  clearing localStorage, or closing/reopening the tab (the cookie persists).
  It CAN be bypassed by clearing cookies, using a private window, or a
  different browser — a known, disclosed limitation (there is no real
  identity to bind an anonymous user to, so this is a best-effort browser-
  level restriction, not a security boundary).
- The AnonymousUsage table stores ONLY the session id + a timestamp —
  never the query text, never anything about the analysis. "Has this
  session_id already analyzed something" is the entire question it answers.
- An anonymous analysis is never written to the "issues" table at all (see
  issue_service.analyze_issue — user_id=None skips the save entirely).
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app import config  # noqa: F401
from app.config import ANON_SESSION_COOKIE_NAME, ANON_SESSION_COOKIE_MAX_AGE_SECONDS
from app.database import get_db
from app.deps import get_current_user, get_current_user_optional
from app.models.anonymous_usage import AnonymousUsage
from app.models.case import LegalCase
from app.models.issue import IssueAnalysis
from app.models.user import User
from app.schemas.issue import IssueAnalysisRequest, IssueAnalysisResponse
from app.services.issue_service import analyze_issue

from llm_client import LLMConfigError, LLMTruncatedError
from rag_engine import RAGEngineError

logger = logging.getLogger("legal_ai.issues")

router = APIRouter(prefix="/api/issues", tags=["issues"])


@router.post("/analyze", response_model=IssueAnalysisResponse)
def analyze(
    request: IssueAnalysisRequest,
    http_request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    # Authenticated callers: no limit, always saved, always their own.
    if current_user is not None:
        case = None
        if request.case_id is not None:
            # NEVER trust a case_id from the client. 404 for both "no such
            # case" and "someone else's case" — indistinguishable on purpose.
            case = (
                db.query(LegalCase)
                .filter(LegalCase.id == request.case_id, LegalCase.user_id == current_user.id)
                .first()
            )
            if case is None:
                raise HTTPException(status_code=404, detail="Case not found.")
        return _run_analysis(request.query, db, user_id=current_user.id, case=case)

    # Anonymous caller. Follow-ups belong to a case, and cases exist only for
    # accounts — an anonymous request naming one is refused outright.
    if request.case_id is not None:
        raise HTTPException(status_code=401, detail="Follow-up questions require an account. Please log in or create one.")

    # Enforce the one-time allowance server-side.
    session_id = http_request.cookies.get(ANON_SESSION_COOKIE_NAME)

    if session_id:
        already_used = db.query(AnonymousUsage).filter(AnonymousUsage.session_id == session_id).first()
        if already_used:
            raise HTTPException(
                status_code=401,
                detail="You've already used your one free anonymous analysis. "
                       "Please log in or create an account to continue.",
            )
    else:
        session_id = str(uuid.uuid4())
        response.set_cookie(
            key=ANON_SESSION_COOKIE_NAME,
            value=session_id,
            max_age=ANON_SESSION_COOKIE_MAX_AGE_SECONDS,
            httponly=True,
            samesite="lax",
        )

    result = _run_analysis(request.query, db, user_id=None)

    # Mark this session as having used its allowance ONLY after a successful
    # analysis — a failed attempt (e.g. LLM unavailable) should not burn the
    # user's one anonymous try.
    try:
        db.add(AnonymousUsage(session_id=session_id))
        db.commit()
    except Exception:
        logger.exception("Failed to record anonymous usage — allowing this request through, "
                          "but the one-time limit may not be enforced for this session")
        db.rollback()

    return result


def _run_analysis(query: str, db: Session, user_id, case=None):
    try:
        return analyze_issue(query, db, user_id, case)

    except RAGEngineError as e:
        logger.error("RAG engine unavailable: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Legal analysis could not be completed: the retrieval system is unavailable.",
        )

    except LLMConfigError as e:
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
        # Log the exception TYPE only, never its message: _extract_json()'s
        # message embeds up to 500 chars of the raw LLM output, which can echo
        # the user's own (potentially sensitive) query text back verbatim.
        logger.error("Analyzer output could not be parsed (%s) — message withheld from logs "
                      "because it may contain echoed user content", type(e).__name__)
        raise HTTPException(
            status_code=500,
            detail="Legal analysis could not be completed due to an internal processing error.",
        )

    except Exception:
        logger.exception("Unexpected error during legal issue analysis")
        raise HTTPException(status_code=500, detail="Legal analysis could not be completed.")


@router.get("")
def list_issues(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Authentication required. Filtered by owner at the DATABASE level —
    never fetch all rows and filter in Python/frontend."""
    try:
        rows = (
            db.query(IssueAnalysis)
            .filter(IssueAnalysis.user_id == current_user.id)
            .order_by(IssueAnalysis.created_at.desc())
            .all()
        )
        return [
            {
                "id": row.id,
                "query": row.query,
                "issue_type": row.issue_type,
                "case_id": row.case_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    except Exception:
        logger.exception("Database error while listing issue analyses")
        raise HTTPException(status_code=500, detail="Could not retrieve issue history.")


@router.get("/{issue_id}")
def get_issue(issue_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        row = db.query(IssueAnalysis).filter(IssueAnalysis.id == issue_id).first()
    except Exception:
        logger.exception("Database error while fetching issue analysis id=%s", issue_id)
        raise HTTPException(status_code=500, detail="Could not retrieve the requested issue analysis.")

    # 404 (not 403) for both "doesn't exist" AND "exists but isn't yours" —
    # deliberately indistinguishable, so a caller can't use the status code
    # to probe which issue_ids exist for other users.
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Issue analysis not found.")

    return {
        "id": row.id,
        "query": row.query,
        "case_id": row.case_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        **(row.full_result or {}),
    }


@router.get("/{issue_id}/report.pdf")
def export_issue_report(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exports a single issue brief as downloadable PDF.
    Deterministic in-memory generation; zero storage.
    """
    issue_data = get_issue(issue_id, db, current_user)
    try:
        from app.services import pdf_service
        pdf_bytes = pdf_service.generate_issue_pdf(issue_data)
    except Exception:
        logger.exception("Failed to generate PDF for issue_id=%s", issue_id)
        raise HTTPException(status_code=500, detail="Could not generate issue PDF report.")

    from datetime import datetime, timezone
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"issue_report_{issue_id}_{date_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )

