from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import decode_access_token
from app.services.demo import is_expired


def get_current_user(
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Reads the JWT from the httpOnly cookie and returns the User, or 401s so
    the frontend redirects to login."""
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_id = decode_access_token(access_token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.is_demo and is_expired(user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Demo session expired")

    return user


def require_real_user(current_user: User = Depends(get_current_user)) -> User:
    """For endpoints that touch a real bank. Demo accounts run on sample data."""
    if current_user.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The demo runs on sample data, so connecting a real bank is turned off. Sign up to link yours.",
        )
    return current_user
