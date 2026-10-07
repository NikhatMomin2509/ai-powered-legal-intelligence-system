"""
models/document.py — SQLAlchemy model for an uploaded + analyzed document.

document_id is a separate public-facing UUID string (not the integer primary
key) — generated at upload time, used in URLs, so the API never exposes raw
DB row ids for documents.

extracted_text_preview deliberately stores only a short preview, not the
full extracted text a second time — full clause text already lives inside
full_result's risky_clauses, so a separate full-text column would duplicate
the same content unnecessarily (per the Phase 5D "do not store
unnecessarily huge duplicate text" instruction).
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func

from app.database import Base


class DocumentAnalysis(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(64), unique=True, nullable=False, index=True)

    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    document_type = Column(String(200), nullable=True)
    status = Column(String(50), nullable=False, default="uploaded")  # uploaded | analyzed | failed

    extracted_text_preview = Column(Text, nullable=True)  # first ~1000 chars only, see docstring
    risk_score = Column(Integer, nullable=True)
    risk_level = Column(String(20), nullable=True)

    full_result = Column(JSON, nullable=True)  # complete analysis: clauses, risk flags, explanations

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
