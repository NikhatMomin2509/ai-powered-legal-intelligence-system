"""
routers/auth.py — POST /api/auth/register, POST /api/auth/login, GET /api/auth/me.

No logout endpoint: JWTs here are stateless (no server-side revocation
list), so "logout" is simply the frontend discarding its stored token —
there is nothing for the backend to do. See auth_service.py's docstring and
the final report's "Security limitations" section for what this trades away.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import DUMMY_PASSWORD_HASH, hash_password, verify_password, create_access_token

logger = logging.getLogger("legal_ai.auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, created_at=user.created_at.isoformat())


@router.post("/register", response_model=TokenResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        # Deliberately vague — do not reveal via a different error shape
        # whether registration failed for "email taken" vs anything else.
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    try:
        user = User(email=request.email, password_hash=hash_password(request.password))
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        logger.exception("Failed to create user account")
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not create account.")

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user=_user_response(user))


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()

    # Deliberately identical error for "no such user" and "wrong password" —
    # distinguishing them lets an attacker enumerate registered emails.
    invalid_credentials = HTTPException(status_code=401, detail="Incorrect email or password.")

    if user is None:
        # Burn the same bcrypt time as a real check so response timing can't
        # reveal whether the email is registered (see auth_service.DUMMY_PASSWORD_HASH).
        verify_password(request.password, DUMMY_PASSWORD_HASH)
        raise invalid_credentials
    if not verify_password(request.password, user.password_hash):
        raise invalid_credentials

    token = create_access_token(user.id, user.email)
    return TokenResponse(access_token=token, user=_user_response(user))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return _user_response(current_user)
