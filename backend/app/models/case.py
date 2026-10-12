"""
models/case.py — a "legal case session": a group of related questions (an
initial question plus follow-ups) belonging to ONE authenticated user.

Only authenticated analyses ever create a case. An anonymous analysis never
touches this table (or any table that stores query content) — see
routers/issues.py and issue_service.py.

title is just the first question, truncated, so the History view has
something human-readable to show; it is the user's own text, owned by that
user, and subject to the same ownership filtering as everything else.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database import Base


class LegalCase(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
