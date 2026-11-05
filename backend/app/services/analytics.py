"""First-party usage analytics: what people do in Wallit, kept in our own
Postgres table, with no third-party tracker.

Events come from two places:
  - the backend records what actually happened (a sign-up, a bank linked, a
    message sent to the assistant), so those counts can't be inflated by a
    page refresh or an ad blocker;
  - the frontend sends page views, which are the only way to count anonymous
    visitors before they sign up or start the demo.

Nothing personal or financial is stored: no emails, amounts or merchant names.
Demo accounts are tagged, so every number can be reported with and without
them. summary() is what /admin/analytics and scripts/analytics_report.py show."""
import logging
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analytics_event import AnalyticsEvent

logger = logging.getLogger(__name__)

# Events the backend records. Anything else passed to track() is a bug.
SERVER_EVENTS = {
    "signup",
    "login",
    "demo_started",
    "bank_linked",
    "resync",
    "chat_message",
    "forecast_viewed",
    "budget_set",
    "transaction_recategorized",
    "plan_created",
}
# Pages the frontend may report. A fixed list, so nothing like an id or a query
# string can end up in the table.
TRACKED_PAGES = {"/", "/demo", "/signup", "/login", "/dashboard", "/calendar", "/subscriptions", "/assistant"}

# What counts as using a feature, for the adoption table.
FEATURES = {
    "Forecast / safe to spend": ("forecast_viewed", None),
    "Assistant": ("chat_message", None),
    "Set a budget": ("budget_set", None),
    "Fixed a category": ("transaction_recategorized", None),
    "Created a savings plan": ("plan_created", None),
    "Bill calendar": ("page_view", "/calendar"),
    "Subscriptions page": ("page_view", "/subscriptions"),
    "Linked a bank": ("bank_linked", None),
}


def track(db: Session, name: str, user=None, *, visitor_id: str | None = None, **properties) -> None:
    """Record one event. Never raises: analytics must not break the request.

    Call it after the request's own commit, since a failure here rolls back
    whatever the session still has pending."""
    if name not in SERVER_EVENTS and name != "page_view":
        raise ValueError(f"unknown analytics event {name!r}")
    try:
        db.add(
            AnalyticsEvent(
                name=name,
                user_id=user.id if user is not None else None,
                is_demo=bool(user is not None and user.is_demo),
                visitor_id=visitor_id,
                properties=properties,
            )
        )
        db.commit()
    except Exception:
        logger.exception("Couldn't record analytics event %s", name)
        db.rollback()


def _group_stats(events: list[AnalyticsEvent]) -> dict:
    by_user: dict = defaultdict(list)
    for e in events:
        if e.user_id is not None:
            by_user[e.user_id].append(e)
    active = len(by_user)

    returning = sum(1 for evs in by_user.values() if len({e.created_at.date() for e in evs}) >= 2)

    # Time from first to last event, per user per day: a rough session length.
    session_minutes = []
    for evs in by_user.values():
        days = defaultdict(list)
        for e in evs:
            days[e.created_at.date()].append(e.created_at)
        for stamps in days.values():
            session_minutes.append((max(stamps) - min(stamps)).total_seconds() / 60)

    adoption = {}
    for label, (name, page) in FEATURES.items():
        users = {
            u for u, evs in by_user.items()
            if any(e.name == name and (page is None or (e.properties or {}).get("page") == page) for e in evs)
        }
        adoption[label] = {"users": len(users), "share": round(len(users) / active, 3) if active else None}

    chat_counts = [sum(1 for e in evs if e.name == "chat_message") for evs in by_user.values()]
    chat_users = [c for c in chat_counts if c]
    return {
        "active_users": active,
        "returning_users": returning,
        "median_session_minutes": round(statistics.median(session_minutes), 1) if session_minutes else None,
        "chat_messages": sum(chat_counts),
        "median_chat_messages_per_chatting_user": statistics.median(chat_users) if chat_users else None,
        "feature_adoption": adoption,
    }


def summary(db: Session, days: int = 30, now: datetime | None = None) -> dict:
    """Usage over the last `days` days, real accounts and demo accounts apart."""
    now = now or datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    events = (
        db.query(AnalyticsEvent)
        .filter(AnalyticsEvent.created_at >= since, AnalyticsEvent.created_at <= now)
        .all()
    )
    first = db.query(func.min(AnalyticsEvent.created_at)).scalar()

    real = [e for e in events if not e.is_demo]
    demo = [e for e in events if e.is_demo]

    # Visitors are browsers, not people: one person on a phone and a laptop is two.
    landing = {e.visitor_id for e in events if e.name == "page_view" and (e.properties or {}).get("page") == "/" and e.visitor_id}
    demo_visitors = {e.visitor_id for e in demo if e.visitor_id}
    real_visitors = {e.visitor_id for e in real if e.visitor_id and e.user_id is not None}

    return {
        "window_days": days,
        "from": since.isoformat(),
        "to": now.isoformat(),
        "tracking_since": first.isoformat() if first else None,
        "real_accounts": {
            **_group_stats(real),
            "signups": sum(1 for e in real if e.name == "signup"),
            "banks_linked": sum(1 for e in real if e.name == "bank_linked"),
        },
        "demo_accounts": {
            **_group_stats(demo),
            "demo_sessions_started": sum(1 for e in demo if e.name == "demo_started"),
        },
        "funnel": {
            "landing_page_visitors": len(landing),
            "of_those_tried_demo": len(landing & demo_visitors),
            "of_those_signed_in_to_a_real_account": len(landing & real_visitors),
        },
    }
