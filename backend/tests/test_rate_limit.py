from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.services import rate_limit
from app.services.auth import hash_password
from app.services.rate_limit import SlidingWindowLimiter


def test_limiter_counts_per_key_and_forgets_old_hits(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("app.services.rate_limit.time.monotonic", lambda: clock[0])
    limiter = SlidingWindowLimiter(limit=2, window_seconds=60)

    assert limiter.allow("a") and limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")

    clock[0] += 61
    assert limiter.allow("a")


def _client(db):
    app.dependency_overrides[get_db] = lambda: db
    rate_limit.reset_all()
    return TestClient(app)


def test_login_is_limited_per_ip_and_email(db, user):
    user.password_hash = hash_password("correct-horse")
    db.flush()
    client = _client(db)
    try:
        for _ in range(rate_limit.login_limiter.limit):
            r = client.post("/api/v1/auth/login", json={"email": user.email, "password": "wrong-guess"})
            assert r.status_code == 401
        blocked = client.post("/api/v1/auth/login", json={"email": user.email, "password": "correct-horse"})
        assert blocked.status_code == 429
        # a different account from the same network isn't affected
        other = client.post("/api/v1/auth/login", json={"email": "someone@example.com", "password": "x"})
        assert other.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_signup_is_limited_per_ip(db):
    client = _client(db)
    try:
        for i in range(rate_limit.signup_limiter.limit):
            r = client.post(
                "/api/v1/auth/signup",
                json={
                    "email": f"new{i}@example.com",
                    "password": "long-enough-pw",
                    "first_name": "New",
                    "last_name": "User",
                    "date_of_birth": "1995-04-02",
                },
            )
            assert r.status_code == 201
        client.cookies.clear()
        r = client.post(
            "/api/v1/auth/signup",
            json={"email": "one-more@example.com", "password": "long-enough-pw", "first_name": "A",
                  "last_name": "B", "date_of_birth": "1995-04-02"},
        )
        assert r.status_code == 429
    finally:
        app.dependency_overrides.clear()


def test_chat_is_limited_per_user(db, monkeypatch):
    monkeypatch.setattr("app.routers.chat.run_chat", lambda db, user, messages: "ok")
    client = _client(db)
    try:
        client.post("/api/v1/demo/session")
        monkeypatch.setattr(rate_limit.chat_limiter, "limit", 3)
        body = {"messages": [{"role": "user", "content": "hi"}]}
        assert [client.post("/api/v1/chat", json=body).status_code for _ in range(4)] == [200, 200, 200, 429]
    finally:
        app.dependency_overrides.clear()
