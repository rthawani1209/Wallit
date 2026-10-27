from datetime import date

from app.services.budgets import get_budget_progress

from .conftest import add_txn


def test_transfers_get_no_budget_row(db, user, account, categories):
    today = date.today()
    add_txn(db, account, categories["Food"], 45, today, "Chipotle")
    add_txn(db, account, categories["Transfer"], 1500, today, "Transfer to Savings")

    names = {b.category_name for b in get_budget_progress(db, user)}

    assert "Food" in names
    assert "Transfer" not in names
