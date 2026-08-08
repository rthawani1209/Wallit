import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.plaid import ExchangeTokenRequest, LinkTokenResponse
from app.services import categorization, encryption, plaid as plaid_service

router = APIRouter(prefix="/plaid", tags=["plaid"])


@router.post("/link-token", response_model=LinkTokenResponse)
def create_link_token(current_user: User = Depends(get_current_user)):
    """
    Step 1 of Plaid flow: create a short-lived Link token.
    The frontend passes this to Plaid's JS widget to open the bank-connection UI.
    """
    try:
        token = plaid_service.create_link_token(str(current_user.id))
        return {"link_token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plaid error: {str(e)}")


@router.post("/exchange-token")
def exchange_token(
    body: ExchangeTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Step 2: exchange the public token Plaid Link gives us for a permanent access token,
    then immediately pull accounts and transactions for this user.
    """
    try:
        access_token = plaid_service.exchange_public_token(body.public_token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plaid exchange error: {str(e)}")

    # Store the access token encrypted — Plaid tokens are sensitive credentials
    current_user.plaid_access_token = encryption.encrypt(access_token)
    db.commit()

    # Pull accounts and upsert into our DB
    accounts_data = plaid_service.get_accounts(access_token)
    for a in accounts_data:
        existing = db.query(Account).filter(Account.plaid_account_id == a["plaid_account_id"]).first()
        if existing:
            existing.current_balance = a["current_balance"]
        else:
            db.add(Account(user_id=current_user.id, **a))
    db.commit()

    # Pull transactions and store them
    db_accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    account_map = {a.plaid_account_id: a.id for a in db_accounts}
    category_map = {c.name: c.id for c in db.query(Category).all()}

    transactions, cursor = plaid_service.sync_transactions(access_token)
    # Right after linking, Plaid may still be generating/enriching the item's
    # transaction history — the first sync call can return a partial batch with
    # personal_finance_category missing on recent entries. An empty poll doesn't
    # mean backfill is done (just that nothing new landed yet), so keep polling
    # for a fixed budget rather than stopping at the first empty result.
    for _ in range(5):
        time.sleep(2)
        more, cursor = plaid_service.sync_transactions(access_token, cursor)
        transactions.extend(more)

    for t in transactions:
        plaid_acct_id = t.pop("plaid_account_id")
        pfc = t.pop("personal_finance_category")
        account_id = account_map.get(plaid_acct_id)
        if not account_id:
            continue
        existing = db.query(Transaction).filter(
            Transaction.plaid_transaction_id == t["plaid_transaction_id"]
        ).first()
        if not existing:
            category_name = categorization.resolve_category(t.get("merchant_name"), pfc)
            category_id = category_map.get(category_name) or category_map.get(categorization.FALLBACK_CATEGORY)
            db.add(Transaction(account_id=account_id, category_id=category_id, **t))
    db.commit()

    return {"message": "Bank connected and transactions synced"}
