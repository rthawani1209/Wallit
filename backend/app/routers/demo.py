from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import _set_auth_cookie
from app.schemas.auth import UserResponse
from app.services import demo
from app.services.auth import decode_access_token
from app.services.client_ip import client_ip
from app.services.rate_limit import demo_limiter

router = APIRouter(prefix="/demo", tags=["demo"])

@router.post("/session", response_model=UserResponse)
def start_demo_session(
    request: Request,
    response: Response,
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """Sign the visitor into a fresh demo account with sample data, or back into
    the one they already have, so refreshing /demo doesn't spawn new users."""
    if access_token:
        user_id = decode_access_token(access_token)
        existing = db.query(User).filter(User.id == user_id).first() if user_id else None
        if existing and existing.is_demo and not demo.is_expired(existing):
            return existing

    # Soft per-IP cap; the eviction below is what really keeps the demo up.
    if not demo_limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many demo sessions from this network. Try again in an hour.")
    # At the global cap, make room by dropping the oldest demo accounts rather
    # than refusing, so the demo never goes dark for the next visitor.
    demo.evict_oldest_demo_users(db, keep=demo.MAX_LIVE_DEMO_USERS - 1)

    user = demo.create_demo_user(db)
    _set_auth_cookie(response, str(user.id))
    return user
