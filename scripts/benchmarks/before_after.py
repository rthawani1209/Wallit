"""Measure one version of the Wallit backend against a simulated bank.

Run it once against a checkout of the old code and once against the new code,
each with its own empty database, and compare the JSON it prints. See
docs/BENCHMARKS.md for the exact commands and the results.

    python scripts/benchmarks/before_after.py --backend path/to/backend \
        --database-url postgresql://ci:ci@localhost:5432/bench

What it does, the same way for both versions:
  1. Signs up a user and links a fake bank holding 8 months of history
     (1,200+ transactions, the last few still pending), through the real
     /plaid/exchange-token endpoint.
  2. Simulates one day passing at the bank: a few new purchases, pending
     charges that post under a new id, and one charge whose amount changes.
  3. Presses resync (/plaid/resync) and records how long it took, how many
     Plaid pages and rows it processed, and how many SQL statements it ran.
  4. Compares what ended up in the database with what the bank actually holds.
  5. Tries 25 wrong passwords in a row, and times logins for a known and an
     unknown email.

Only Plaid's HTTP client is replaced. Everything else, including the waits the
code does on purpose, runs as written."""
import argparse
import json
import os
import random
import statistics
import subprocess
import sys
import time
from datetime import date, timedelta

PAGE_SIZE = 100  # Plaid's default page size for /transactions/sync
HISTORY_DAYS = 240
TODAY = date(2026, 11, 4)

MERCHANTS = [
    ("Whole Foods", "FOOD_AND_DRINK", "FOOD_AND_DRINK_GROCERIES", 30, 140),
    ("Trader Joe's", "FOOD_AND_DRINK", "FOOD_AND_DRINK_GROCERIES", 20, 90),
    ("Chipotle", "FOOD_AND_DRINK", "FOOD_AND_DRINK_FAST_FOOD", 10, 18),
    ("Starbucks", "FOOD_AND_DRINK", "FOOD_AND_DRINK_COFFEE", 4, 9),
    ("Uber", "TRANSPORTATION", "TRANSPORTATION_TAXIS_AND_RIDE_SHARES", 9, 35),
    ("Shell", "TRANSPORTATION", "TRANSPORTATION_GAS", 30, 60),
    ("Amazon", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES", 12, 120),
    ("Target", "GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_SUPERSTORES", 15, 110),
    ("AMC Theatres", "ENTERTAINMENT", "ENTERTAINMENT_TV_AND_MOVIES", 14, 40),
    ("CVS", "MEDICAL", "MEDICAL_PHARMACIES_AND_SUPPLEMENTS", 8, 45),
]
MONTHLY = [
    ("Netflix", "ENTERTAINMENT", "ENTERTAINMENT_TV_AND_MOVIES", 17.99, 12),
    ("Spotify", "ENTERTAINMENT", "ENTERTAINMENT_MUSIC_AND_AUDIO", 11.99, 3),
    ("Planet Fitness", "PERSONAL_CARE", "PERSONAL_CARE_GYMS_AND_FITNESS_CENTERS", 24.99, 20),
    ("Avalon Apartments", "RENT_AND_UTILITIES", "RENT_AND_UTILITIES_RENT", 1650.00, 1),
]


class FakeBank:
    """Stands in for Plaid's API client. Its event log is what /transactions/sync
    pages through; a cursor is just a position in that log."""

    def __init__(self):
        self.rng = random.Random(7)
        self.log: list[tuple[str, dict]] = []
        self.current: dict[str, dict] = {}  # what the bank holds right now
        self.pages_served = 0
        self._next_id = 0
        self._build_history()

    def _txn(self, account, amount, day, merchant, primary, detailed, pending=False):
        self._next_id += 1
        return {
            "transaction_id": f"txn-{self._next_id:05d}",
            "account_id": account,
            "amount": round(amount, 2),
            "date": day,
            "merchant_name": merchant,
            "name": merchant,
            "pending": pending,
            "personal_finance_category": {"primary": primary, "detailed": detailed},
        }

    def _add(self, t):
        self.log.append(("added", t))
        self.current[t["transaction_id"]] = t

    def _build_history(self):
        start = TODAY - timedelta(days=HISTORY_DAYS)
        for i in range(HISTORY_DAYS + 1):
            day = start + timedelta(days=i)
            for _ in range(self.rng.randint(3, 6)):
                m, p, d, lo, hi = self.rng.choice(MERCHANTS)
                account = "acct-credit" if self.rng.random() < 0.6 else "acct-checking"
                self._add(self._txn(account, self.rng.uniform(lo, hi), day, m, p, d))
            for m, p, d, amount, dom in MONTHLY:
                if day.day == dom:
                    self._add(self._txn("acct-checking", amount, day, m, p, d))
            if day.day in (1, 15):
                self._add(self._txn("acct-checking", -2900.00, day, "Acme Corp Payroll", "INCOME", "INCOME_WAGES"))
        # The last two days' card purchases haven't posted yet.
        self.pending = []
        for _ in range(8):
            m, p, d, lo, hi = self.rng.choice(MERCHANTS[:6])
            t = self._txn("acct-credit", self.rng.uniform(lo, hi), TODAY - timedelta(days=1), m, p, d, pending=True)
            self._add(t)
            self.pending.append(t)

    def one_day_passes(self):
        """What a real bank does overnight."""
        tomorrow = TODAY + timedelta(days=1)
        # Pending charges post under a new transaction id; the pending one is removed.
        for t in self.pending:
            self.log.append(("removed", {"transaction_id": t["transaction_id"]}))
            del self.current[t["transaction_id"]]
            posted = dict(t, pending=False)
            self._next_id += 1
            posted["transaction_id"] = f"txn-{self._next_id:05d}"
            if t["merchant_name"] == "Chipotle":
                posted["amount"] = round(t["amount"] * 1.2, 2)  # tip added when it posts
            self._add(posted)
        # A few new purchases.
        for _ in range(5):
            m, p, d, lo, hi = self.rng.choice(MERCHANTS)
            self._add(self._txn("acct-credit", self.rng.uniform(lo, hi), tomorrow, m, p, d))
        # A merchant corrects an already-posted charge.
        fixed = next(t for t in self.current.values() if t["merchant_name"] == "Whole Foods" and not t["pending"])
        fixed = dict(fixed, amount=round(fixed["amount"] + 10, 2))
        self.log.append(("modified", fixed))
        self.current[fixed["transaction_id"]] = fixed

    # --- the parts of plaid_api.PlaidApi the app calls ---

    def item_public_token_exchange(self, request):
        return {"access_token": "access-sandbox-bench", "item_id": "item-bench"}

    def item_get(self, request):
        return {"item": {"item_id": "item-bench"}}

    def accounts_get(self, request):
        return {
            "accounts": [
                {"account_id": "acct-checking", "name": "Everyday Checking", "type": "depository",
                 "balances": {"current": 4210.55}},
                {"account_id": "acct-credit", "name": "Rewards Card", "type": "credit",
                 "balances": {"current": 812.40}},
            ]
        }

    def transactions_sync(self, request):
        self.pages_served += 1
        try:
            cursor = request["cursor"]
        except Exception:  # unset optional field
            cursor = None
        pos = int(cursor) if cursor else 0
        page = self.log[pos:pos + PAGE_SIZE]
        out = {"added": [], "modified": [], "removed": []}
        for kind, t in page:
            out[kind].append(t)
        end = pos + len(page)
        return {
            **out,
            "next_cursor": str(end),
            "has_more": end < len(self.log),
            "transactions_update_status": "HISTORICAL_UPDATE_COMPLETE",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", required=True, help="the backend/ folder of the checkout to measure")
    parser.add_argument("--database-url", required=True, help="an empty Postgres database; it gets wiped")
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    backend = os.path.abspath(args.backend)
    os.environ["DATABASE_URL"] = args.database_url
    os.environ.setdefault("JWT_SECRET_KEY", "benchmark-only-secret")
    os.environ.setdefault("ENCRYPTION_KEY", "JCFWz8YjTTWCN32T0OFOPn4zpLM6pETHafofeIjGnjY=")
    os.environ["ANTHROPIC_API_KEY"] = ""

    from sqlalchemy import create_engine, event, text

    with create_engine(args.database_url).begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=backend, check=True, capture_output=True)

    sys.path.insert(0, backend)
    os.chdir(backend)
    from fastapi.testclient import TestClient

    from app.database import engine
    from app.main import app
    from app.services import plaid as plaid_service

    bank = FakeBank()
    plaid_service._get_client = lambda: bank

    statements = {"n": 0}
    event.listen(engine, "before_cursor_execute", lambda *a, **k: statements.__setitem__("n", statements["n"] + 1))

    client = TestClient(app)  # no `with`, so the nightly scheduler doesn't start
    signup = {
        "email": "bench@example.com", "password": "correct-horse-battery",
        "first_name": "Bench", "last_name": "User", "date_of_birth": "1999-04-12",
    }
    r = client.post("/api/v1/auth/signup", json=signup)
    assert r.status_code == 201, r.text

    def timed(call):
        bank.pages_served, statements["n"] = 0, 0
        start = time.perf_counter()
        response = call()
        assert response.status_code == 200, response.text
        return response, {
            "seconds": round(time.perf_counter() - start, 2),
            "plaid_pages": bank.pages_served,
            "sql_statements": statements["n"],
        }

    _, link = timed(lambda: client.post("/api/v1/plaid/exchange-token", json={"public_token": "public-bench"}))
    history = len(bank.log)
    bank.one_day_passes()
    response, resync = timed(lambda: client.post("/api/v1/plaid/resync"))
    resync["transactions_processed"] = response.json()["transactions_touched"]

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT plaid_transaction_id, amount FROM transactions")).all()
    stored_spend = sum(float(a) for _, a in rows if float(a) > 0)
    true_spend = sum(t["amount"] for t in bank.current.values() if t["amount"] > 0)
    ids = {i for i, _ in rows}
    accuracy = {
        "rows_stored": len(rows),
        "rows_at_bank": len(bank.current),
        "rows_bank_no_longer_has": len(ids - set(bank.current)),
        "spend_stored": round(stored_spend, 2),
        "spend_at_bank": round(true_spend, 2),
        "spend_error": round(stored_spend - true_spend, 2),
    }

    # Brute force: 25 wrong passwords in a row from one address.
    codes = [client.post("/api/v1/auth/login", json={"email": signup["email"], "password": f"guess-{i}"}).status_code
             for i in range(25)]
    brute_force = {"attempts": 25, "rejected_as_wrong_password": codes.count(401), "blocked": codes.count(429)}

    # Login timing for an email that exists vs one that doesn't. Limits are
    # cleared first where the version has them, so this measures timing only.
    try:
        from app.services import rate_limit
        rate_limit.reset_all()
        clear = rate_limit.reset_all
    except ImportError:
        clear = lambda: None

    def median_ms(email, n=15):
        samples = []
        for _ in range(n):
            clear()
            start = time.perf_counter()
            client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password"})
            samples.append((time.perf_counter() - start) * 1000)
        return round(statistics.median(samples), 1)

    timing = {"known_email_ms": median_ms(signup["email"]), "unknown_email_ms": median_ms("nobody@example.com")}

    print(json.dumps({
        "label": args.label,
        "bank_history_transactions": history,
        "link": link,
        "resync": resync,
        "accuracy_after_resync": accuracy,
        "brute_force": brute_force,
        "login_timing": timing,
    }, indent=2))


if __name__ == "__main__":
    main()
