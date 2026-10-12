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

from app.models.case import LegalCase
from app.models.issue import IssueAnalysis

from issue_analyzer import analyze_legal_issue

logger = logging.getLogger("legal_ai.issue_service")


MAX_CONTEXT_TURNS = 3          # how many earlier turns of a case feed a follow-up
MAX_CONTEXT_FIELD_CHARS = 400  # each earlier question/summary is truncated to this


def build_contextual_query(db: Session, case: LegalCase, follow_up: str) -> str:
    """Composes the text handed to the (unmodified) analyzer for a follow-up.

    issue_analyzer.analyze_legal_issue() takes a single string and has no
    notion of conversation history, and it is deliberately NOT modified for
    this feature. Without earlier context, a follow-up like "What if he
    claims I damaged the apartment?" is unanswerable (who is "he"?). So the
    earlier questions and the analyzer's own earlier summaries are folded
    into the string here, in the service layer.

    Scoped to ONE case that the caller has already been verified to own.
    """
    turns = (
        db.query(IssueAnalysis)
        .filter(IssueAnalysis.case_id == case.id, IssueAnalysis.user_id == case.user_id)
        .order_by(IssueAnalysis.created_at.desc(), IssueAnalysis.id.desc())
        .limit(MAX_CONTEXT_TURNS)
        .all()
    )
    turns.reverse()  # oldest first
    lines = []
    for t in turns:
        lines.append(f"Earlier question: {(t.query or '')[:MAX_CONTEXT_FIELD_CHARS]}")
        if t.issue_summary:
            lines.append(f"Earlier assessment summary: {t.issue_summary[:MAX_CONTEXT_FIELD_CHARS]}")
    history = "\n".join(lines)
    return (
        f"Context from earlier in this same legal matter:\n{history}\n\n"
        f"New follow-up question (answer it in light of the context above): {follow_up}"
    )


def analyze_issue(query: str, db: Session, user_id: int | None, case: LegalCase | None = None) -> dict:
    """Calls the EXISTING Phase 4 analyzer directly, then saves the result
    ONLY if user_id is provided. This is the privacy/auth feature's core
    rule for Module 2: an anonymous analysis (user_id=None) is NEVER
    written to the database, in any form — not even without a name attached.
    It exists only in the HTTP response for this one request and, on the
    frontend, in that browser tab's in-memory state.

    case: an already-ownership-verified LegalCase to attach a follow-up to.
    If None and user_id is set, a NEW case is created — but only AFTER the
    analysis succeeded, so a failed analysis never leaves an empty case.

    Any exception analyze_legal_issue() raises (RAGEngineError,
    LLMConfigError, LLMTruncatedError, ValueError from JSON parsing, etc.)
    is intentionally left to propagate BEFORE we ever attempt to save —
    routers/issues.py turns those into safe HTTP responses.
    """
    analysis_input = build_contextual_query(db, case, query) if case is not None else query
    result = analyze_legal_issue(analysis_input)

    if user_id is None:
        return result

    issue_id, case_id = _save_issue_analysis(query, result, db, user_id, case)
    # Identifiers are added to the RESPONSE only (after saving), so the stored
    # full_result stays exactly what the analyzer produced.
    return {**result, "issue_id": issue_id, "case_id": case_id}


def _save_issue_analysis(query: str, result: dict, db: Session, user_id: int, case: LegalCase | None):
    """Best-effort save; returns (issue_id, case_id), or (None, None) on failure.
    A database problem must not turn an already-successful legal analysis into
    a failed API response — failures are logged, not raised. `query` is what
    the USER TYPED (a follow-up is stored as typed, never as the composite
    context string)."""
    try:
        if case is None:
            case = LegalCase(user_id=user_id, title=query.strip()[:200])
            db.add(case)
            db.flush()  # assigns case.id within the same transaction as the issue below

        record = IssueAnalysis(
            user_id=user_id,
            case_id=case.id,
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
        return record.id, case.id
    except Exception:
        logger.exception("Failed to save issue analysis to the database (query will still be returned to the client)")
        db.rollback()
        return None, None
