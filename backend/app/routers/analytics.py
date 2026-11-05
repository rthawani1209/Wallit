import uuid

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import analytics
from app.services.auth import decode_access_token
from app.services.client_ip import client_ip
from app.services.rate_limit import events_limiter

router = APIRouter(tags=["analytics"])


class PageViewRequest(BaseModel):
    page: str
    visitor_id: uuid.UUID


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
def page_view(
    body: PageViewRequest,
    request: Request,
    access_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """A page view from the frontend. Works signed out too, so visits to the
    landing page count. Unknown pages are ignored rather than stored."""
    if body.page not in analytics.TRACKED_PAGES or not events_limiter.allow(client_ip(request)):
        return
    user = None
    if access_token and (user_id := decode_access_token(access_token)):
        try:
            user = db.get(User, uuid.UUID(user_id))
        except ValueError:
            user = None
    analytics.track(db, "page_view", user, visitor_id=str(body.visitor_id), page=body.page)


@router.get("/admin/analytics")
def usage_summary(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Usage numbers for the owner. Anyone else gets a 404, as if it didn't exist."""
    if current_user.is_demo or current_user.email.lower() not in settings.admin_email_list:
        raise HTTPException(status_code=404, detail="Not Found")
    return analytics.summary(db, days)
