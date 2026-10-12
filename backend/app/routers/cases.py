"""
routers/cases.py — Case management and case report export endpoints.

Endpoints:
- GET /api/cases: List authenticated user's cases with turn counts and last activity.
- GET /api/cases/{case_id}: Retrieve complete case thread (oldest to newest) with sanitized results.
- GET /api/cases/{case_id}/report.pdf: Export full multi-turn case brief as PDF.

Privacy & Ownership:
- All endpoints strictly require authentication.
- Foreign cases and nonexistent cases return the exact same 404 response.
- Underscore-prefixed diagnostic/internal keys are stripped from responses and reports.
"""

from datetime import datetime, timezone
import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.case import LegalCase
from app.models.issue import IssueAnalysis
from app.models.user import User
from app.services import pdf_service

logger = logging.getLogger("legal_ai.cases")

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("")
def list_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List authenticated user's cases, newest activity first.
    Database-level ownership filtering.
    """
    try:
        sub = (
            db.query(
                IssueAnalysis.case_id.label("case_id"),
                func.count(IssueAnalysis.id).label("q_count"),
                func.max(IssueAnalysis.created_at).label("last_active"),
            )
            .filter(IssueAnalysis.user_id == current_user.id)
            .group_by(IssueAnalysis.case_id)
            .subquery()
        )

        rows = (
            db.query(LegalCase, sub.c.q_count, sub.c.last_active)
            .outerjoin(sub, LegalCase.id == sub.c.case_id)
            .filter(LegalCase.user_id == current_user.id)
            .order_by(
                func.coalesce(sub.c.last_active, LegalCase.created_at).desc(),
                LegalCase.id.desc(),
            )
            .all()
        )

        return [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "last_activity": (last_act.isoformat() if last_act else c.created_at.isoformat()) if (last_act or c.created_at) else None,
                "question_count": count or 0,
            }
            for c, count, last_act in rows
        ]
    except Exception:
        logger.exception("Database error while listing cases")
        raise HTTPException(status_code=500, detail="Could not retrieve case history.")


@router.get("/{case_id}")
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all turns of a case from oldest to newest.
    Returns 404 for nonexistent or foreign cases.
    """
    try:
        case = (
            db.query(LegalCase)
            .filter(LegalCase.id == case_id, LegalCase.user_id == current_user.id)
            .first()
        )
    except Exception:
        logger.exception("Database error while fetching case id=%s", case_id)
        raise HTTPException(status_code=500, detail="Could not retrieve the requested case.")

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    try:
        issues = (
            db.query(IssueAnalysis)
            .filter(IssueAnalysis.case_id == case.id, IssueAnalysis.user_id == current_user.id)
            .order_by(IssueAnalysis.created_at.asc(), IssueAnalysis.id.asc())
            .all()
        )
    except Exception:
        logger.exception("Database error while fetching turns for case id=%s", case_id)
        raise HTTPException(status_code=500, detail="Could not retrieve case turns.")

    turns = []
    for issue in issues:
        raw_result = issue.full_result or {
            "issue_summary": issue.issue_summary,
            "legal_domain": issue.issue_type,
            "key_facts": issue.key_facts,
            "missing_facts": issue.missing_facts,
            "relevant_laws": issue.relevant_laws,
            "relevant_cases": issue.relevant_cases,
            "supporting_considerations": (issue.assessment or {}).get("supporting_considerations")
            if isinstance(issue.assessment, dict)
            else [],
            "opposing_considerations": (issue.assessment or {}).get("opposing_considerations")
            if isinstance(issue.assessment, dict)
            else [],
            "possible_actions_or_remedies": issue.possible_actions_or_remedies,
            "lawyer_specialization": issue.lawyer_specialization,
            "disclaimer": issue.disclaimer,
        }
        clean_result = {k: v for k, v in raw_result.items() if not k.startswith("_")}
        turns.append(
            {
                "issue_id": issue.id,
                "query": issue.query,
                "created_at": issue.created_at.isoformat() if issue.created_at else None,
                "result": clean_result,
            }
        )

    return {
        "case_id": case.id,
        "title": case.title,
        "created_at": case.created_at.isoformat() if case.created_at else None,
        "turns": turns,
    }


@router.get("/{case_id}/report.pdf")
def export_case_report(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exports full case brief as downloadable PDF.
    Deterministic in-memory generation; zero storage.
    """
    case_data = get_case(case_id, db, current_user)
    turns = case_data.get("turns", [])

    try:
        pdf_bytes = pdf_service.generate_case_pdf(
            case_title=case_data.get("title", f"Case #{case_id}"),
            case_id=case_id,
            turns=turns,
        )
    except Exception:
        logger.exception("Failed to generate PDF for case_id=%s", case_id)
        raise HTTPException(status_code=500, detail="Could not generate case PDF report.")

    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"case_report_{case_id}_{date_str}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Content-Disposition": f'inline; filename="{filename}"',
        },
    )
