from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.plaid import AccountResponse, ExchangeTokenRequest, LinkTokenResponse, TransactionResponse
from app.services import encryption, plaid as plaid_service

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

    transactions, _ = plaid_service.sync_transactions(access_token)
    for t in transactions:
        plaid_acct_id = t.pop("plaid_account_id")
        account_id = account_map.get(plaid_acct_id)
        if not account_id:
            continue
        existing = db.query(Transaction).filter(
            Transaction.plaid_transaction_id == t["plaid_transaction_id"]
        ).first()
        if not existing:
            db.add(Transaction(account_id=account_id, **t))
    db.commit()

    return {"message": "Bank connected and transactions synced"}


@router.get("/accounts", response_model=list[AccountResponse])
def get_accounts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Account).filter(Account.user_id == current_user.id).all()


@router.get("/transactions", response_model=list[TransactionResponse])
def get_transactions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    account_ids = [a.id for a in accounts]
    return (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids))
        .order_by(Transaction.date.desc())
        .limit(100)
        .all()
    )
