"""Linking several banks and syncing them incrementally, against a fake Plaid."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.account import Account
from app.models.plaid_item import PlaidItem
from app.models.transaction import Transaction
from app.services import encryption, item_sync
from app.services.auth import create_access_token

FOOD = {"primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_RESTAURANT"}


def txn(txn_id, account_id, amount=20.0):
    return {
        "plaid_transaction_id": txn_id,
        "amount": amount,
        "merchant_name": "Pho Bac",
        "date": date(2026, 10, 3),
        "plaid_account_id": account_id,
        "personal_finance_category": FOOD,
    }


class FakePlaid:
    """Each bank is a token with accounts and a list of change batches. A cursor
    is just how many batches the caller has already seen."""

    def __init__(self):
        self.banks = {}
        self.sync_calls = []

    def add_bank(self, token, item_id, account_ids, first_batch):
        self.banks[token] = {"item_id": item_id, "accounts": account_ids, "batches": [first_batch]}

    def push(self, token, upserts=(), removed=()):
        self.banks[token]["batches"].append((list(upserts), list(removed)))

    def exchange_public_token(self, public_token):
        return public_token, self.banks[public_token]["item_id"]

    def get_accounts(self, token):
        return [
            {"plaid_account_id": a, "name": a, "type": "depository", "current_balance": 100.0}
            for a in self.banks[token]["accounts"]
        ]

    def sync_transactions(self, token, cursor=None):
        self.sync_calls.append((token, cursor))
        seen = int(cursor or 0)
        upserts, removed = [], []
        for batch_upserts, batch_removed in self.banks[token]["batches"][seen:]:
            upserts.extend(batch_upserts)
            removed.extend(batch_removed)
        return upserts, removed, str(len(self.banks[token]["batches"])), item_sync.HISTORY_COMPLETE


@pytest.fixture
def fake_plaid(monkeypatch):
    fake = FakePlaid()
    for name in ("exchange_public_token", "get_accounts", "sync_transactions"):
        monkeypatch.setattr(f"app.services.plaid.{name}", getattr(fake, name))
    return fake


@pytest.fixture
def client(db, user):
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    c.cookies.set("access_token", create_access_token(str(user.id)))
    yield c
    app.dependency_overrides.clear()


def link(client, token, name):
    r = client.post("/api/v1/plaid/exchange-token", json={"public_token": token, "institution_name": name})
    assert r.status_code == 200, r.text


def test_second_bank_keeps_the_first(client, db, user, fake_plaid):
    fake_plaid.add_bank("tok-chase", "item-chase", ["chase-chk"], ([txn("c1", "chase-chk")], []))
    fake_plaid.add_bank("tok-amex", "item-amex", ["amex-card"], ([txn("a1", "amex-card")], []))
    link(client, "tok-chase", "Chase")
    link(client, "tok-amex", "Amex")

    items = db.query(PlaidItem).filter_by(user_id=user.id).order_by(PlaidItem.created_at).all()
    assert [encryption.decrypt(i.access_token) for i in items] == ["tok-chase", "tok-amex"]

    listed = client.get("/api/v1/plaid/items").json()
    assert {(i["institution_name"], i["account_count"]) for i in listed} == {("Chase", 1), ("Amex", 1)}

    # a resync reaches both banks, not just the most recent one
    fake_plaid.push("tok-chase", upserts=[txn("c2", "chase-chk")])
    fake_plaid.push("tok-amex", upserts=[txn("a2", "amex-card")])
    assert client.post("/api/v1/plaid/resync").status_code == 200
    ids = {t.plaid_transaction_id for t in db.query(Transaction).join(Account).filter(Account.user_id == user.id)}
    assert ids == {"c1", "c2", "a1", "a2"}


def test_resync_sends_the_saved_cursor(client, db, user, fake_plaid):
    fake_plaid.add_bank("tok-chase", "item-chase", ["chase-chk"], ([txn("c1", "chase-chk"), txn("p1", "chase-chk")], []))
    link(client, "tok-chase", "Chase")
    item = db.query(PlaidItem).filter_by(user_id=user.id).one()
    assert item.cursor == "1" and item.last_synced_at is not None

    # the pending charge posts: Plaid removes p1 and adds the posted version
    fake_plaid.push("tok-chase", upserts=[txn("p1-posted", "chase-chk", 22.0)], removed=["p1"])
    fake_plaid.sync_calls.clear()
    client.post("/api/v1/plaid/resync")

    assert fake_plaid.sync_calls == [("tok-chase", "1")]
    db.refresh(item)
    assert item.cursor == "2"
    ids = {t.plaid_transaction_id for t in db.query(Transaction).join(Account).filter(Account.plaid_item_id == item.id)}
    assert ids == {"c1", "p1-posted"}


def test_relinking_the_same_bank_reuses_its_item(client, db, user, fake_plaid):
    fake_plaid.add_bank("tok-chase", "item-chase", ["chase-chk"], ([txn("c1", "chase-chk")], []))
    link(client, "tok-chase", "Chase")
    link(client, "tok-chase", None)

    items = db.query(PlaidItem).filter_by(user_id=user.id).all()
    assert len(items) == 1 and items[0].institution_name == "Chase"
    assert db.query(Account).filter_by(user_id=user.id).count() == 1


def test_resync_without_a_bank_is_rejected(client):
    assert client.post("/api/v1/plaid/resync").status_code == 400
