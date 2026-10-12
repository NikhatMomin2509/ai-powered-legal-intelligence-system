"""
auth_service.py — password hashing and JWT issuance/verification.

Password hashing: uses the `bcrypt` library DIRECTLY rather than passlib.
This is a deliberate choice, not an oversight — passlib's bcrypt backend has
known compatibility problems with recent bcrypt releases (passlib tries to
read a `__about__.__version__` attribute bcrypt 4.x+ no longer exposes,
causing a loud warning or outright failure depending on versions). Calling
bcrypt's own hashpw/checkpw directly is simpler, avoids that whole class of
version-skew bug, and is still the same underlying, well-vetted algorithm
bcrypt/passlib both wrap.

JWT: stateless (no server-side revocation list / refresh-token table). This
is a deliberate scope decision for an academic project — see the "Security
limitations" section of the final report for what this trades away.
"""

import datetime
import logging

import bcrypt
import jwt

from app.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRY_HOURS

logger = logging.getLogger("legal_ai.auth")


def hash_password(plain_password: str) -> str:
    """Returns a bcrypt hash. The plaintext password is never stored,
    logged, or returned from this function in any other form."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError) as e:
        # A malformed stored hash should never crash the login attempt —
        # treat it as "doesn't match" and log server-side only.
        logger.error("Password verification failed to even run (malformed hash?): %s", e)
        return False


# A real bcrypt hash of a throwaway string, computed once at import. login()
# verifies the submitted password against THIS when the email isn't registered,
# so "unknown email" costs the same ~bcrypt time as "wrong password". Without
# it, the unknown-email path returned in ~2 ms versus ~280 ms for a real
# account (measured) — identical error TEXT but a trivially measurable timing
# difference that lets anyone enumerate which emails are registered.
DUMMY_PASSWORD_HASH = hash_password("timing-equalization-only-never-a-real-password")


def create_access_token(user_id: int, email: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user_id),  # JWT convention: "sub" (subject) identifies the token's owner
        "email": email,
        "iat": now,
        "exp": now + datetime.timedelta(hours=JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


class InvalidTokenError(Exception):
    pass


def decode_access_token(token: str) -> dict:
    """Returns the decoded payload, or raises InvalidTokenError for any
    problem (expired, malformed, wrong signature) — callers don't need to
    know which specific PyJWT exception type was involved."""
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Token has expired.")
    except jwt.InvalidTokenError as e:
        raise InvalidTokenError(f"Invalid token: {e}")
