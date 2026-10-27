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
from app.services.transaction_sync import prune_missing_transactions, remove_transactions, save_transactions

router = APIRouter(prefix="/plaid", tags=["plaid"])


def _fetch_all_transactions(access_token: str) -> tuple[list[dict], list[str]]:
    """Full history for this token as (upserts, removed_ids), deduplicated so a
    transaction that was added and then modified or removed shows up once."""
    # Right after linking, Plaid may still be enriching the item's history, so an
    # empty poll doesn't mean it's done — poll a few extra times before giving up.
    upserts, removed, cursor = plaid_service.sync_transactions(access_token)
    for _ in range(5):
        time.sleep(2)
        more, more_removed, cursor = plaid_service.sync_transactions(access_token, cursor)
        upserts.extend(more)
        removed.extend(more_removed)

    removed_set = set(removed)
    latest = {t["plaid_transaction_id"]: t for t in upserts if t["plaid_transaction_id"] not in removed_set}
    return list(latest.values()), list(removed_set)


def _sync_into_db(db: Session, user: User, access_token: str) -> int:
    db_accounts = db.query(Account).filter(Account.user_id == user.id).all()
    account_map = {a.plaid_account_id: a.id for a in db_accounts}
    category_map = {c.name: c.id for c in db.query(Category).all()}

    upserts, removed = _fetch_all_transactions(access_token)
    touched = save_transactions(db, account_map, category_map, upserts)
    db.flush()
    touched += remove_transactions(db, list(account_map.values()), removed)

    # Each sync starts from an empty cursor, so `upserts` is this bank's complete
    # current history and any other row we hold for its accounts is stale (usually a
    # pending charge saved before removals were handled). Only accounts this token
    # returned are pruned, so a different bank's rows are never touched.
    synced_accounts = {account_map[t["plaid_account_id"]] for t in upserts if t["plaid_account_id"] in account_map}
    touched += prune_missing_transactions(
        db, list(synced_accounts), {t["plaid_transaction_id"] for t in upserts}
    )
    db.commit()
    return touched


@router.post("/link-token", response_model=LinkTokenResponse)
def create_link_token(current_user: User = Depends(get_current_user)):
    """Short-lived token the frontend passes to Plaid's Link widget."""
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
    """Exchange the public token from Plaid Link for a permanent access token,
    then pull accounts and transactions for this user."""
    try:
        access_token = plaid_service.exchange_public_token(body.public_token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plaid exchange error: {str(e)}")

    current_user.plaid_access_token = encryption.encrypt(access_token)
    db.commit()

    accounts_data = plaid_service.get_accounts(access_token)
    for a in accounts_data:
        existing = db.query(Account).filter(Account.plaid_account_id == a["plaid_account_id"]).first()
        if existing:
            existing.current_balance = a["current_balance"]
        else:
            db.add(Account(user_id=current_user.id, **a))
    db.commit()

    _sync_into_db(db, current_user, access_token)
    detection.run_detection(db, current_user.id)

    return {"message": "Bank connected and transactions synced"}


@router.post("/resync")
def resync(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Re-fetch full transaction history and refresh categorization on every row."""
    if not current_user.plaid_access_token:
        raise HTTPException(status_code=400, detail="No bank account connected")
    access_token = encryption.decrypt(current_user.plaid_access_token)

    touched = _sync_into_db(db, current_user, access_token)
    detection.run_detection(db, current_user.id)

    return {"message": "Resynced", "transactions_touched": touched}
