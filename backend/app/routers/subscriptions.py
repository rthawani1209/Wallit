import re
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.category import Category
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscriptions import CalendarEvent, SubscriptionResponse
from app.services.detection import NON_DISCRETIONARY_CATEGORIES, project_occurrences

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[SubscriptionResponse])
def get_subscriptions(
    include_inactive: bool = Query(False),
    discretionary_only: bool = Query(
        False, description="Exclude bills/debt/housing — only genuinely cancellable subscriptions"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detected recurring charges, soonest due first. Populated by detection.run_detection,
    which runs automatically after every Plaid sync/resync and on the nightly schedule."""
    query = db.query(Subscription).filter(Subscription.user_id == current_user.id)
    if not include_inactive:
        query = query.filter(Subscription.is_active.is_(True))
    subs = query.order_by(Subscription.next_estimated_date.asc().nulls_last()).all()

    category_names = {c.id: c.name for c in db.query(Category).all()}
    if discretionary_only:
        subs = [
            s for s in subs if category_names.get(s.category_id) not in NON_DISCRETIONARY_CATEGORIES
        ]

    return [
        SubscriptionResponse(
            id=s.id,
            merchant_name=s.merchant_name,
            amount=float(s.amount),
            billing_interval=s.billing_interval,
            next_estimated_date=s.next_estimated_date,
            category_name=category_names.get(s.category_id),
            cheaper_alternative=s.cheaper_alternative,
            is_active=s.is_active,
        )
        for s in subs
    ]


MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


@router.get("/calendar", response_model=list[CalendarEvent])
def get_calendar(
    month: str = Query(..., description="YYYY-MM, e.g. 2026-09"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Every active subscription/bill occurrence projected onto the requested month,
    for the calendar view. Navigate forward or backward by passing a different month —
    projection works in both directions from each subscription's known due date."""
    if not MONTH_PATTERN.match(month):
        raise HTTPException(status_code=422, detail="month must be in YYYY-MM format")
    year, month_num = (int(p) for p in month.split("-"))
    if not (1 <= month_num <= 12):
        raise HTTPException(status_code=422, detail="month must be between 01 and 12")

    range_start = date(year, month_num, 1)
    next_month = date(year + (month_num == 12), (month_num % 12) + 1, 1)
    range_end = next_month - timedelta(days=1)

    subs = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id, Subscription.is_active.is_(True))
        .all()
    )
    category_names = {c.id: c.name for c in db.query(Category).all()}

    events = []
    for sub in subs:
        for occurrence_date in project_occurrences(sub, range_start, range_end):
            events.append(
                CalendarEvent(
                    date=occurrence_date,
                    merchant_name=sub.merchant_name,
                    amount=float(sub.amount),
                    category_name=category_names.get(sub.category_id),
                    billing_interval=sub.billing_interval,
                )
            )

    events.sort(key=lambda e: e.date)
    return events
