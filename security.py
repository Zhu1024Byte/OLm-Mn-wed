"""Password hashing, random password generation and JWT helpers."""

import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"
SECRET_FILE = Path("data/.secret_key")

# Module-level cache so the secret is only resolved once per process
_secret: str | None = None


def _get_or_create_secret() -> str:
    """Return the JWT secret, generating and persisting one when needed."""
    global _secret
    if _secret:
        return _secret

    if settings.secret_key:
        _secret = settings.secret_key
    elif SECRET_FILE.exists():
        _secret = SECRET_FILE.read_text(encoding="utf-8").strip()
    else:
        _secret = secrets.token_hex(32)
        SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
        SECRET_FILE.write_text(_secret, encoding="utf-8")

    return _secret


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt (returns a ``$2b$`` string)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash. Never raises."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def generate_random_password(length: int = 16) -> str:
    """Generate a cryptographically secure, URL-safe random password."""
    return secrets.token_urlsafe(length)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def create_access_token(user_id: int, username: str) -> str:
    """Create a signed JWT access token for the given user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, _get_or_create_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT. Returns the payload dict or ``None``."""
    try:
        return jwt.decode(token, _get_or_create_secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
