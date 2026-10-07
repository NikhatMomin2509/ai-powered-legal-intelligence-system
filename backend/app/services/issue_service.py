"""
issue_service.py — thin pass-through to the existing, untouched Phase 4
analyzer, plus (Phase 5C) persisting successful results to SQLite. Contains
NO retrieval, no LLM calls, no business logic of its own beyond that save —
its only job is to be the one place routers/issues.py imports from, so the
router never has to know that analyze_legal_issue actually lives at the
project root.
"""

import logging

from sqlalchemy.orm import Session

# Importing app.config FIRST (even though we don't use it directly here)
# guarantees the PROJECT_ROOT sys.path bootstrap has run before the next
# import, regardless of what order other modules get imported in — see
# config.py's docstring for why that bootstrap is needed at all.
from app import config  # noqa: F401

from app.models.issue import IssueAnalysis

from issue_analyzer import analyze_legal_issue

logger = logging.getLogger("legal_ai.issue_service")


def analyze_issue(query: str, db: Session) -> dict:
    """Calls the EXISTING Phase 4 analyzer directly, then saves the result.
    Any exception analyze_legal_issue() raises (RAGEngineError,
    LLMConfigError, LLMTruncatedError, ValueError from JSON parsing, etc.)
    is intentionally left to propagate BEFORE we ever attempt to save —
    routers/issues.py turns those into safe HTTP responses, and nothing is
    written to the database for a failed analysis.
    """
    result = analyze_legal_issue(query)
    _save_issue_analysis(query, result, db)
    return result


def _save_issue_analysis(query: str, result: dict, db: Session) -> None:
    """Best-effort save. A database problem must not turn an already-
    successful legal analysis into a failed API response for the user —
    so failures here are logged, not raised. The API still returns the
    analysis either way; it just won't appear in history if this fails.
    """
    try:
        record = IssueAnalysis(
            query=query,
            issue_summary=result.get("issue_summary"),
            issue_type=result.get("legal_domain"),
            key_facts=result.get("key_facts"),
            missing_facts=result.get("missing_facts"),
            relevant_laws=result.get("relevant_laws"),
            relevant_cases=result.get("relevant_cases"),
            assessment={
                "supporting_considerations": result.get("supporting_considerations"),
                "opposing_considerations": result.get("opposing_considerations"),
            },
            possible_actions_or_remedies=result.get("possible_actions_or_remedies"),
            lawyer_specialization=result.get("lawyer_specialization"),
            disclaimer=result.get("disclaimer"),
            full_result=result,
        )
        db.add(record)
        db.commit()
    except Exception:
        logger.exception("Failed to save issue analysis to the database (query will still be returned to the client)")
        db.rollback()
