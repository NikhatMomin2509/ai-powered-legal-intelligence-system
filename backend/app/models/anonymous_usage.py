"""
models/anonymous_usage.py — backend-enforced "one anonymous legal issue
analysis per browser" tracking.

Deliberately minimal: this table stores ONLY a session identifier and a
timestamp. It never stores the anonymous user's query, their IP address, or
anything about the analysis itself — the existence of a row for a given
session_id is the entire signal ("this session has used its one allowed
anonymous analysis"), nothing more. This is what makes "never permanently
store anonymous legal queries" actually true, not just a promise in a
docstring — there is no column here that COULD hold query content.
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class AnonymousUsage(Base):
    __tablename__ = "anonymous_usage"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
