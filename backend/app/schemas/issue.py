"""
schemas/issue.py — Pydantic models for POST /api/issues/analyze.

Request is strictly validated (empty/whitespace-only/too-short all rejected
with a clear message). Response is deliberately NOT pinned to a rigid
field-by-field model: analyze_legal_issue() returns a dict whose shape has
already evolved across Phase 4 (e.g. the "source"/"category" fields added to
relevant_laws, the "_raw_retrieval_counts" diagnostic field) and may evolve
again. A strict response_model would silently drop or reshape anything that
doesn't match — exactly what "preserve the complete analyzer output" rules
out. IssueAnalysisResponse exists only so Swagger has something to show.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator

MIN_QUERY_LENGTH = 10


class IssueAnalysisRequest(BaseModel):
    query: str
    # Optional: continue an existing case session (follow-up question).
    # Requires authentication AND ownership of that case — enforced server-side.
    case_id: Optional[int] = None

    @field_validator("query")
    @classmethod
    def query_must_be_meaningful(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Legal query cannot be empty or whitespace-only.")
        if len(stripped) < MIN_QUERY_LENGTH:
            raise ValueError(
                f"Legal query must be at least {MIN_QUERY_LENGTH} characters long — "
                f"please describe your legal issue in a bit more detail."
            )
        return stripped  # store the trimmed version, not the raw whitespace-padded input


# Documentation-only — see module docstring for why this isn't an enforced response_model.
IssueAnalysisResponse = Dict[str, Any]
