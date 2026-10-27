import time
from collections import defaultdict, deque

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
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
    """The visitor's IP as reported by our own proxies, never by the client.
    Taking the leftmost X-Forwarded-For entry would let anyone dodge the cap
    by sending a made-up header on every request."""
    hops = settings.proxy_hops
    entries = [e.strip() for e in request.headers.get("x-forwarded-for", "").split(",") if e.strip()]
    if hops > 0 and entries:
        # A shorter chain than expected means a proxy didn't append; the nearest
        # entry we have is still better than the proxy's own socket address.
        return entries[-hops] if len(entries) >= hops else entries[0]
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
    # At the global cap, make room by dropping the oldest demo accounts rather
    # than refusing, so the demo never goes dark for the next visitor.
    demo.evict_oldest_demo_users(db, keep=demo.MAX_LIVE_DEMO_USERS - 1)

    user = demo.create_demo_user(db)
    _set_auth_cookie(response, str(user.id))
    return user
