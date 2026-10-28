from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.config import settings
from app.database import get_db
from app.main import app
from app.models.account import Account
from app.models.category import Category
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.transaction import Transaction
from app.models.user import User
from app.services import demo, rate_limit


def test_seed_is_realistic_and_runs_through_real_detection(db):
    user = demo.create_demo_user(db)

    account_ids = [a.id for a in db.query(Account).filter_by(user_id=user.id)]
    txns = db.query(Transaction).filter(Transaction.account_id.in_(account_ids)).all()
    assert len(txns) > 300
    assert min(t.date for t in txns) <= date.today() - timedelta(days=200)

    subs = {s.merchant_name: s for s in db.query(Subscription).filter_by(user_id=user.id, is_active=True)}
    assert {"Netflix", "Spotify", "Crunch Fitness", "Xfinity Internet"} <= set(subs)
    assert "Trader Joe's" not in subs  # weekly groceries vary too much to be a subscription
    assert subs["Netflix"].cheaper_alternative

    flagged = {t.merchant_name: t.anomaly_reason for t in txns if t.is_anomaly}
    assert "Netflix" in flagged and "15.49 to $17.99" in flagged["Netflix"]
    assert "Ticketmaster" in flagged and "Canlis" in flagged


def test_seed_categorizes_through_the_plaid_mapping(db):
    user = demo.create_demo_user(db)
    names = {c.id: c.name for c in db.query(Category).all()}
    account_ids = [a.id for a in db.query(Account).filter_by(user_id=user.id)]
    by_merchant = {
        t.merchant_name: names[t.category_id]
        for t in db.query(Transaction).filter(Transaction.account_id.in_(account_ids))
    }
    assert by_merchant["Maple Court Apartments"] == "Housing"
    assert by_merchant["Seattle City Light"] == "Utilities"
    assert by_merchant["Transfer to High-Yield Savings"] == "Savings"
    assert by_merchant["Venmo"] == "Transfer"
    assert by_merchant["Northwind Labs Payroll"] == "Income"


def test_expired_demo_users_are_deleted_with_their_data(db):
    old = demo.create_demo_user(db)
    fresh = demo.create_demo_user(db)
    old.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db.commit()

    assert demo.delete_expired_demo_users(db) == 1

    assert db.query(User).filter_by(id=old.id).first() is None
    assert db.query(Account).filter_by(user_id=old.id).count() == 0
    assert db.query(Plan).filter_by(user_id=old.id).count() == 0
    assert db.query(User).filter_by(id=fresh.id).first() is not None


def _client(db):
    app.dependency_overrides[get_db] = lambda: db
    rate_limit.reset_all()
    return TestClient(app)


def test_demo_session_endpoint_signs_in_and_reuses_the_session(db):
    client = _client(db)
    try:
        first = client.post("/api/v1/demo/session")
        assert first.status_code == 200 and first.json()["is_demo"] is True
        assert client.get("/api/v1/auth/me").json()["id"] == first.json()["id"]

        again = client.post("/api/v1/demo/session")
        assert again.json()["id"] == first.json()["id"]

        summary = client.get("/api/v1/transactions/cashflow").json()
        assert any(m["income"] > 0 for m in summary)
    finally:
        app.dependency_overrides.clear()


def test_demo_users_cannot_touch_plaid(db):
    client = _client(db)
    try:
        client.post("/api/v1/demo/session")
        assert client.post("/api/v1/plaid/link-token").status_code == 403
        assert client.post("/api/v1/plaid/resync").status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_demo_chat_is_capped(db):
    client = _client(db)
    try:
        user_id = client.post("/api/v1/demo/session").json()["id"]
        user = db.query(User).filter_by(id=user_id).one()
        user.demo_chat_count = demo.DEMO_CHAT_LIMIT
        db.commit()

        reply = client.post("/api/v1/chat", json={"messages": [{"role": "user", "content": "hi"}]})
        assert reply.status_code == 200
        assert "limit" in reply.json()["message"]
    finally:
        app.dependency_overrides.clear()


def test_new_demo_sessions_are_rate_limited_per_ip():
    rate_limit.reset_all()
    for _ in range(rate_limit.demo_limiter.limit):
        assert rate_limit.demo_limiter.allow("203.0.113.9")
    assert not rate_limit.demo_limiter.allow("203.0.113.9")
    assert rate_limit.demo_limiter.allow("198.51.100.4")


def test_spoofed_forwarded_for_does_not_reset_the_cap(db, monkeypatch):
    # Behind two proxies the real visitor is second from the right; a fake
    # leftmost entry from the client must not count as a new visitor.
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    client = _client(db)
    try:
        for i in range(rate_limit.demo_limiter.limit):
            client.cookies.clear()
            headers = {"x-forwarded-for": f"10.0.0.{i}, 198.51.100.7, 76.76.21.1"}
            assert client.post("/api/v1/demo/session", headers=headers).status_code == 200
        client.cookies.clear()
        spoofed = {"x-forwarded-for": "1.2.3.4, 198.51.100.7, 76.76.21.1"}
        assert client.post("/api/v1/demo/session", headers=spoofed).status_code == 429
    finally:
        app.dependency_overrides.clear()


def test_global_cap_evicts_the_oldest_instead_of_refusing(db, monkeypatch):
    monkeypatch.setattr(demo, "MAX_LIVE_DEMO_USERS", 2)
    first = demo.create_demo_user(db)
    first.created_at = datetime.now(timezone.utc) - timedelta(hours=3)
    db.commit()
    demo.create_demo_user(db)
    client = _client(db)
    try:
        assert client.post("/api/v1/demo/session").status_code == 200
        assert db.query(User).filter_by(id=first.id).first() is None
        assert db.query(User).filter(User.is_demo.is_(True)).count() == 2
    finally:
        app.dependency_overrides.clear()


def test_creating_a_demo_makes_no_claude_calls(db, monkeypatch):
    # With a key configured, any fallthrough in categorization or detection would
    # reach Anthropic. Record every client construction and require none.
    import anthropic

    calls = []

    def record(*args, **kwargs):
        calls.append(kwargs)
        raise RuntimeError("Claude must not be called while building a demo")

    monkeypatch.setattr(settings, "anthropic_api_key", "sk-test-not-real")
    monkeypatch.setattr(anthropic, "Anthropic", record)

    demo.create_demo_user(db)
    assert calls == []

    # and the trap does fire on a real fallthrough, so the check above means something
    from app.services.categorization import resolve_category

    resolve_category("ZZQX Holdings LLC", None, 12.0)
    assert len(calls) == 1
