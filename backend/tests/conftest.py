"""Tests run against a real Postgres (the queries use Postgres-only functions like
to_char), migrated once per session. Each test runs inside a transaction that's
rolled back afterwards, so the services can call commit() freely."""
import os
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")
os.environ.setdefault("ENCRYPTION_KEY", "JCFWz8YjTTWCN32T0OFOPn4zpLM6pETHafofeIjGnjY=")
os.environ.setdefault("ANTHROPIC_API_KEY", "")

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def engine():
    if "DATABASE_URL" not in os.environ:
        pytest.skip("DATABASE_URL not set; these tests need a throwaway Postgres database")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND_DIR, check=True, capture_output=True)
    eng = create_engine(os.environ["DATABASE_URL"])
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine):
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def categories(db):
    from app.models.category import Category

    return {c.name: c.id for c in db.query(Category).all()}


@pytest.fixture
def user(db):
    from app.models.user import User

    u = User(email=f"test-{uuid.uuid4().hex[:8]}@example.com", first_name="Test", last_name="User")
    db.add(u)
    db.flush()
    return u


@pytest.fixture
def account(db, user):
    from app.models.account import Account

    a = Account(
        user_id=user.id,
        plaid_account_id=f"acct-{uuid.uuid4().hex[:8]}",
        name="Checking",
        type="depository",
        current_balance=2500,
    )
    db.add(a)
    db.flush()
    return a


def add_txn(db, account, category_id, amount, on: date, merchant="Test Merchant"):
    from app.models.transaction import Transaction

    t = Transaction(
        account_id=account.id,
        plaid_transaction_id=f"txn-{uuid.uuid4().hex}",
        amount=amount,
        merchant_name=merchant,
        date=on,
        category_id=category_id,
    )
    db.add(t)
    db.flush()
    return t
