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


def test_limiter_drops_idle_keys(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("app.services.rate_limit.time.monotonic", lambda: clock[0])
    limiter = SlidingWindowLimiter(limit=5, window_seconds=60)

    for i in range(10_000):
        limiter.allow(f"203.0.113.9|user{i}@example.com")
    assert len(limiter) == 10_000

    clock[0] += 61
    for _ in range(rate_limit.SWEEP_EVERY):
        limiter.allow("still-active")
    assert len(limiter) == 1


def _login(client, email, ip):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-guess"},
        headers={"X-Forwarded-For": ip},
    )


def test_one_ip_spraying_many_accounts_is_limited(db, monkeypatch):
    monkeypatch.setattr("app.services.client_ip.settings.trusted_proxy_hops", 1)
    client = _client(db)
    try:
        codes = [_login(client, f"victim{i}@example.com", "198.51.100.7").status_code
                 for i in range(rate_limit.login_ip_limiter.limit + 1)]
        assert codes[:-1] == [401] * rate_limit.login_ip_limiter.limit
        assert codes[-1] == 429
        # another network is unaffected
        assert _login(client, "victim0@example.com", "198.51.100.8").status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_many_ips_guessing_one_account_is_limited(db, user, monkeypatch):
    monkeypatch.setattr("app.services.client_ip.settings.trusted_proxy_hops", 1)
    client = _client(db)
    try:
        limit = rate_limit.login_email_limiter.limit
        codes = [_login(client, user.email, f"192.0.2.{i}").status_code for i in range(limit + 1)]
        assert codes[:-1] == [401] * limit
        assert codes[-1] == 429
    finally:
        app.dependency_overrides.clear()
