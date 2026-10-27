from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.services import categorization


def save_transactions(
    db: Session,
    account_map: dict[str, object],
    category_map: dict[str, object],
    transactions: list[dict],
) -> int:
    """Insert new transactions and refresh categorization on existing ones (but
    never overwrite a manually-recategorized row). Returns rows touched."""
    touched = 0
    for t in transactions:
        t = dict(t)
        plaid_acct_id = t.pop("plaid_account_id")
        pfc = t.pop("personal_finance_category", None)
        account_id = account_map.get(plaid_acct_id)
        if not account_id:
            continue

        category_name = categorization.resolve_category(t.get("merchant_name"), pfc, t.get("amount"))
        category_id = category_map.get(category_name) or category_map.get(categorization.FALLBACK_CATEGORY)
        plaid_primary = (pfc or {}).get("primary")
        plaid_detailed = (pfc or {}).get("detailed")

        existing = (
            db.query(Transaction)
            .filter(Transaction.plaid_transaction_id == t["plaid_transaction_id"])
            .first()
        )
        if existing:
            if not existing.category_is_manual:
                existing.category_id = category_id
            # Plaid reports edits (e.g. a tip added when a restaurant charge posts)
            # through `modified`, so the row has to take the new values.
            existing.amount = t["amount"]
            existing.date = t["date"]
            existing.merchant_name = t.get("merchant_name")
            existing.plaid_category_primary = plaid_primary
            existing.plaid_category_detailed = plaid_detailed
        else:
            db.add(
                Transaction(
                    account_id=account_id,
                    category_id=category_id,
                    plaid_category_primary=plaid_primary,
                    plaid_category_detailed=plaid_detailed,
                    **t,
                )
            )
        touched += 1
    return touched


def remove_transactions(db: Session, account_ids: list, plaid_transaction_ids: list[str]) -> int:
    """Delete rows Plaid says no longer exist (mostly pending charges that posted
    under a new id). Scoped to the user's own accounts."""
    if not plaid_transaction_ids or not account_ids:
        return 0
    return (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.plaid_transaction_id.in_(plaid_transaction_ids),
        )
        .delete(synchronize_session=False)
    )


def prune_missing_transactions(db: Session, account_ids: list, current_ids: set[str]) -> int:
    """After a full sync, drop the user's rows that Plaid no longer returns."""
    if not account_ids or not current_ids:
        return 0
    return (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.plaid_transaction_id.notin_(current_ids),
        )
        .delete(synchronize_session=False)
    )
