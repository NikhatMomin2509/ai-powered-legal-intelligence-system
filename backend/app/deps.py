"""
deps.py — FastAPI dependencies for authentication.

Two variants, used deliberately differently:

- get_current_user: REQUIRES a valid token, raises 401 otherwise. Used by
  every endpoint that must never run anonymously (document upload/analyze,
  GET /api/issues, GET /api/documents, etc.).

- get_current_user_optional: returns the User if a valid token is present,
  or None if no token / an invalid token is present — it does NOT raise.
  Used ONLY by POST /api/issues/analyze, which has genuinely different
  (not just "blocked") behavior for anonymous vs authenticated callers —
  see routers/issues.py for the one-time anonymous allowance logic this
  enables.

Neither of these ever logs a token value or a password.
"""

import logging

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import decode_access_token, InvalidTokenError

logger = logging.getLogger("legal_ai.deps")


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")

    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired session. Please log in again.")
    return user


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    token = _extract_bearer_token(authorization)
    if not token:
        return None
    try:
        payload = decode_access_token(token)
    except InvalidTokenError:
        return None  # an invalid/expired token on the OPTIONAL path is treated as "anonymous", not an error
    user_id = payload.get("sub")
    if not user_id:
        return None
    return db.query(User).filter(User.id == int(user_id)).first()
