from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.services import categorization


def save_transactions(
    db: Session,
    account_map: dict[str, object],
    category_map: dict[str, object],
    transactions: list[dict],
) -> int:
    """
    Insert new transactions and refresh categorization on existing ones (re-running a
    sync should also repair rows that were miscategorized by an earlier, partial sync —
    not just skip them). Returns the number of rows touched.
    """
    touched = 0
    for t in transactions:
        t = dict(t)
        plaid_acct_id = t.pop("plaid_account_id")
        pfc = t.pop("personal_finance_category", None)
        account_id = account_map.get(plaid_acct_id)
        if not account_id:
            continue

        category_name = categorization.resolve_category(t.get("merchant_name"), pfc)
        category_id = category_map.get(category_name) or category_map.get(categorization.FALLBACK_CATEGORY)
        plaid_primary = (pfc or {}).get("primary")
        plaid_detailed = (pfc or {}).get("detailed")

        existing = (
            db.query(Transaction)
            .filter(Transaction.plaid_transaction_id == t["plaid_transaction_id"])
            .first()
        )
        if existing:
            existing.category_id = category_id
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
