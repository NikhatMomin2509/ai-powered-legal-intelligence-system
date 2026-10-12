"""
models/user.py — the account every owned record (issue, document) belongs to.

password_hash stores a bcrypt hash ONLY — the plaintext password is never
written to the database, logged, or stored anywhere, at any point. See
services/auth_service.py for the hashing itself.
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(320), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
