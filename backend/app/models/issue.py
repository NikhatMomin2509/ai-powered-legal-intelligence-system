"""
models/issue.py — SQLAlchemy model for a saved legal issue analysis.

Field mapping note (the Phase 5C spec's field names don't all match
issue_analyzer.analyze_legal_issue()'s output keys 1:1 — documenting the
mapping explicitly rather than leaving it implicit):

  spec field      -> analyzer output key(s)
  ---------------------------------------------------------------
  issue_type      -> legal_domain
  assessment      -> {"supporting_considerations": [...],
                       "opposing_considerations": [...]}  (bundled —
                       the analyzer returns these as two separate list
                       fields; combined here into one JSON object so the
                       "assessment" column means something coherent)
  (everything else matches the analyzer's key names directly)

full_result stores the COMPLETE, unmodified analyzer output dict as JSON —
this is the actual guarantee behind "preserve the complete analyzer output
so future fields aren't silently lost" (Phase 4 already added
_raw_retrieval_counts after this schema could have been designed around an
earlier version of the output; the named columns below are for convenient
querying, full_result is the source of truth).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func

from app.database import Base


class IssueAnalysis(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(Text, nullable=False)

    issue_summary = Column(Text, nullable=True)
    issue_type = Column(String(200), nullable=True, index=True)  # = analyzer's legal_domain
    key_facts = Column(JSON, nullable=True)
    missing_facts = Column(JSON, nullable=True)
    relevant_laws = Column(JSON, nullable=True)
    relevant_cases = Column(JSON, nullable=True)
    assessment = Column(JSON, nullable=True)  # see mapping note above
    possible_actions_or_remedies = Column(JSON, nullable=True)
    lawyer_specialization = Column(String(300), nullable=True)
    disclaimer = Column(Text, nullable=True)

    full_result = Column(JSON, nullable=True)  # complete analyzer output, verbatim

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
