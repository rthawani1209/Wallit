from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Run bcrypt on the plain-text password. Never store the original."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a login attempt against the stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str) -> str:
    """Signed JWT carrying the user's id and an expiry timestamp."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str | None:
    """Verify the JWT signature and return the user_id, or None if invalid/expired."""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload.get("sub")
    except JWTError:
        return None


def create_oauth_state() -> str:
    """Short-lived signed token used as the Google OAuth 'state' param — verified
    on its own signature rather than a stored cookie, since that cookie has to
    survive a redirect out to Google and back (and, in production, a same-domain
    proxy on top of that), which is a fragile round-trip for a cookie to survive."""
    payload = {"purpose": "oauth_state", "exp": datetime.now(timezone.utc) + timedelta(minutes=10)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_oauth_state(token: str) -> bool:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload.get("purpose") == "oauth_state"
    except JWTError:
        return False