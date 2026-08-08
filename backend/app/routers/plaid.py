import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.category import Category
from app.models.user import User
from app.schemas.plaid import ExchangeTokenRequest, LinkTokenResponse
from app.services import detection, encryption, plaid as plaid_service
from app.services.transaction_sync import save_transactions

router = APIRouter(prefix="/plaid", tags=["plaid"])


def _fetch_all_transactions(access_token: str) -> list[dict]:
    """
    Full transaction history for an access token. Right after linking (or when
    forcing a resync), Plaid may still be generating/enriching the item's history —
    an empty poll doesn't mean it's done, just that nothing new landed yet — so this
    polls a fixed number of extra times rather than stopping at the first empty result.
    """
    transactions, cursor = plaid_service.sync_transactions(access_token)
    for _ in range(5):
        time.sleep(2)
        more, cursor = plaid_service.sync_transactions(access_token, cursor)
        transactions.extend(more)
    return transactions


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

    transactions = _fetch_all_transactions(access_token)
    save_transactions(db, account_map, category_map, transactions)
    db.commit()

    detection.run_detection(db, current_user.id)

    return {"message": "Bank connected and transactions synced"}


@router.post("/resync")
def resync(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Re-fetch full transaction history from Plaid and refresh categorization on every
    row (not just new ones). Useful if an earlier sync caught a partial batch, or after
    an improvement to the categorization logic.
    """
    if not current_user.plaid_access_token:
        raise HTTPException(status_code=400, detail="No bank account connected")
    access_token = encryption.decrypt(current_user.plaid_access_token)

    db_accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    account_map = {a.plaid_account_id: a.id for a in db_accounts}
    category_map = {c.name: c.id for c in db.query(Category).all()}

    transactions = _fetch_all_transactions(access_token)
    touched = save_transactions(db, account_map, category_map, transactions)
    db.commit()

    detection.run_detection(db, current_user.id)

    return {"message": "Resynced", "transactions_touched": touched}
