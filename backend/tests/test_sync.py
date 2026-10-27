from datetime import date

from app.models.transaction import Transaction
from app.services.transaction_sync import prune_missing_transactions, remove_transactions, save_transactions

FOOD = {"primary": "FOOD_AND_DRINK", "detailed": "FOOD_AND_DRINK_RESTAURANT"}


def row(txn_id, account, amount=20.0, merchant="Pho Bac", on=date(2026, 9, 3)):
    return {
        "plaid_transaction_id": txn_id,
        "amount": amount,
        "merchant_name": merchant,
        "date": on,
        "plaid_account_id": account.plaid_account_id,
        "personal_finance_category": FOOD,
    }


def test_modified_transaction_takes_new_amount(db, account, categories):
    account_map = {account.plaid_account_id: account.id}
    save_transactions(db, account_map, categories, [row("t1", account, 20.0)])
    db.flush()
    # the restaurant charge posts with the tip added
    save_transactions(db, account_map, categories, [row("t1", account, 24.5)])
    db.flush()

    t = db.query(Transaction).filter_by(plaid_transaction_id="t1").one()
    assert float(t.amount) == 24.5


def test_manual_category_survives_resync(db, account, categories):
    account_map = {account.plaid_account_id: account.id}
    save_transactions(db, account_map, categories, [row("t2", account)])
    db.flush()
    t = db.query(Transaction).filter_by(plaid_transaction_id="t2").one()
    t.category_id = categories["Entertainment"]
    t.category_is_manual = True
    db.flush()

    save_transactions(db, account_map, categories, [row("t2", account)])
    db.flush()

    db.refresh(t)
    assert t.category_id == categories["Entertainment"]


def test_pending_charge_removed_when_it_posts(db, account, categories):
    account_map = {account.plaid_account_id: account.id}
    save_transactions(db, account_map, categories, [row("pending-1", account)])
    db.flush()

    save_transactions(db, account_map, categories, [row("posted-1", account)])
    db.flush()
    remove_transactions(db, [account.id], ["pending-1"])

    ids = {t.plaid_transaction_id for t in db.query(Transaction).filter_by(account_id=account.id)}
    assert ids == {"posted-1"}


def test_full_sync_prunes_stale_rows_only_on_synced_accounts(db, user, account, categories):
    from app.models.account import Account

    other = Account(user_id=user.id, plaid_account_id="other-bank", name="Other", type="credit")
    db.add(other)
    db.flush()
    account_map = {account.plaid_account_id: account.id, other.plaid_account_id: other.id}
    save_transactions(db, account_map, categories, [row("stale", account), row("keep", account)])
    other_row = row("other-bank-txn", account)
    other_row["plaid_account_id"] = "other-bank"
    save_transactions(db, account_map, categories, [other_row])
    db.flush()

    pruned = prune_missing_transactions(db, [account.id], {"keep"})

    remaining = {t.plaid_transaction_id for t in db.query(Transaction).filter(Transaction.account_id.in_([account.id, other.id]))}
    assert pruned == 1
    assert remaining == {"keep", "other-bank-txn"}
