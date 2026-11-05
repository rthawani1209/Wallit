"""Usage analytics: what gets recorded, and that summary() keeps demo and real
accounts apart."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.analytics_event import AnalyticsEvent
from app.models.user import User
from app.services import analytics, rate_limit
from app.services.auth import create_access_token, hash_password

NOW = datetime(2026, 11, 5, 18, 0, tzinfo=timezone.utc)


def event(db, name, user=None, at=NOW, visitor=None, **props):
    db.add(AnalyticsEvent(
        name=name, user_id=user.id if user else None, is_demo=bool(user and user.is_demo),
        visitor_id=visitor, properties=props, created_at=at,
    ))
    db.flush()


@pytest.fixture
def client(db):
    rate_limit.reset_all()
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_user(db, **kw):
    u = User(email=f"a-{uuid.uuid4().hex[:8]}@example.com", **kw)
    db.add(u)
    db.flush()
    return u


def test_track_rejects_unknown_events(db, user):
    with pytest.raises(ValueError):
        analytics.track(db, "made_up_event", user)


def test_summary_separates_demo_from_real(db):
    real = make_user(db)
    demo = make_user(db, is_demo=True)
    event(db, "signup", real, at=NOW - timedelta(days=3))
    event(db, "forecast_viewed", real, at=NOW - timedelta(days=3))
    event(db, "chat_message", real, at=NOW - timedelta(days=1))
    event(db, "chat_message", real, at=NOW - timedelta(days=1, minutes=-6))
    event(db, "demo_started", demo, at=NOW - timedelta(hours=2))
    event(db, "page_view", demo, at=NOW - timedelta(hours=2, minutes=-4), page="/calendar")
    event(db, "chat_message", demo, at=NOW - timedelta(hours=1, minutes=50))
    event(db, "signup", make_user(db), at=NOW - timedelta(days=40))  # outside the window

    s = analytics.summary(db, days=30, now=NOW)
    r, d = s["real_accounts"], s["demo_accounts"]
    assert r["active_users"] == 1 and r["signups"] == 1
    assert r["returning_users"] == 1  # active on two different days
    assert r["chat_messages"] == 2
    assert r["feature_adoption"]["Forecast / safe to spend"] == {"users": 1, "share": 1.0}
    assert r["feature_adoption"]["Bill calendar"]["users"] == 0
    assert d["active_users"] == 1 and d["demo_sessions_started"] == 1
    assert d["median_session_minutes"] == 10.0
    assert d["feature_adoption"]["Bill calendar"]["users"] == 1


def test_funnel_follows_a_browser_from_landing_to_demo(db):
    demo = make_user(db, is_demo=True)
    event(db, "page_view", None, visitor="v1", page="/")
    event(db, "page_view", None, visitor="v2", page="/")
    event(db, "page_view", demo, visitor="v1", page="/dashboard")
    f = analytics.summary(db, days=30, now=NOW + timedelta(minutes=1))["funnel"]
    assert f == {"landing_page_visitors": 2, "of_those_tried_demo": 1, "of_those_signed_in_to_a_real_account": 0}


def test_page_view_endpoint_ignores_unknown_pages(db, client):
    visitor = str(uuid.uuid4())
    assert client.post("/api/v1/events", json={"page": "/", "visitor_id": visitor}).status_code == 204
    assert client.post("/api/v1/events", json={"page": "/transactions/123?x=1", "visitor_id": visitor}).status_code == 204
    rows = db.query(AnalyticsEvent).filter(AnalyticsEvent.visitor_id == visitor).all()
    assert [r.properties["page"] for r in rows] == ["/"]
    assert rows[0].user_id is None


def test_page_view_is_tied_to_the_signed_in_user(db, client, user):
    client.cookies.set("access_token", create_access_token(str(user.id)))
    client.post("/api/v1/events", json={"page": "/dashboard", "visitor_id": str(uuid.uuid4())})
    row = db.query(AnalyticsEvent).filter(AnalyticsEvent.user_id == user.id).one()
    assert row.properties == {"page": "/dashboard"} and row.is_demo is False


def test_login_and_signup_are_recorded(db, client):
    email = f"new-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/api/v1/auth/signup", json={
        "email": email, "password": "long-enough-password", "first_name": "A", "last_name": "B",
        "date_of_birth": "1999-01-01",
    })
    assert r.status_code == 201
    client.post("/api/v1/auth/login", json={"email": email, "password": "long-enough-password"})
    client.post("/api/v1/auth/login", json={"email": email, "password": "wrong"})
    user = db.query(User).filter(User.email == email).one()
    names = [e.name for e in db.query(AnalyticsEvent).filter(AnalyticsEvent.user_id == user.id)]
    assert sorted(names) == ["login", "signup"]  # the failed login isn't counted


def test_admin_summary_is_hidden_from_everyone_else(db, client, monkeypatch):
    from app.config import settings

    owner = make_user(db, password_hash=hash_password("x"))
    other = make_user(db)
    monkeypatch.setattr(settings, "admin_emails", owner.email.upper())

    client.cookies.set("access_token", create_access_token(str(other.id)))
    assert client.get("/api/v1/admin/analytics").status_code == 404
    client.cookies.set("access_token", create_access_token(str(owner.id)))
    r = client.get("/api/v1/admin/analytics?days=7")
    assert r.status_code == 200 and r.json()["window_days"] == 7
