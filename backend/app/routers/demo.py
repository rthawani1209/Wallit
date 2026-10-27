import time
from collections import defaultdict, deque

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.routers.auth import _set_auth_cookie
from app.schemas.auth import UserResponse
from app.services import demo
from app.services.auth import decode_access_token

router = APIRouter(prefix="/demo", tags=["demo"])

# Soft per-IP cap on new demo sessions. In-memory is fine for one process; it
# resets on deploy, and the global MAX_LIVE_DEMO_USERS cap backs it up.
SESSIONS_PER_IP_PER_HOUR = 10
_recent_by_ip: dict[str, deque] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    # Behind Vercel's rewrite and Railway's proxy, the visitor is the first hop.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _allow(ip: str) -> bool:
    now = time.monotonic()
    window = _recent_by_ip[ip]
    while window and now - window[0] > 3600:
        window.popleft()
    if len(window) >= SESSIONS_PER_IP_PER_HOUR:
        return False
    window.append(now)
    return True


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

    if not _allow(_client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many demo sessions from this network. Try again in an hour.")
    if demo.live_demo_count(db) >= demo.MAX_LIVE_DEMO_USERS:
        raise HTTPException(status_code=503, detail="The demo is very busy right now. Try again in a little while.")

    user = demo.create_demo_user(db)
    _set_auth_cookie(response, str(user.id))
    return user
