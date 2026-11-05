from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_real_user
from app.models.account import Account
from app.models.plaid_item import PlaidItem
from app.models.user import User
from app.schemas.plaid import ExchangeTokenRequest, LinkTokenResponse, PlaidItemResponse
from app.services import analytics, detection, encryption, plaid as plaid_service
from app.services.item_sync import sync_item

router = APIRouter(prefix="/plaid", tags=["plaid"])


@router.post("/link-token", response_model=LinkTokenResponse)
def create_link_token(current_user: User = Depends(require_real_user)):
    """Short-lived token the frontend passes to Plaid's Link widget."""
    try:
        token = plaid_service.create_link_token(str(current_user.id))
        return {"link_token": token}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plaid error: {str(e)}")


@router.post("/exchange-token")
def exchange_token(
    body: ExchangeTokenRequest,
    current_user: User = Depends(require_real_user),
    db: Session = Depends(get_db),
):
    """Exchange the public token from Plaid Link for a permanent access token,
    then pull this bank's accounts and transactions. Each bank gets its own
    item, so linking a second one leaves the first alone."""
    try:
        access_token, item_id = plaid_service.exchange_public_token(body.public_token)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Plaid exchange error: {str(e)}")

    # Re-linking the same login (e.g. after a password change) replaces its token
    # and starts its sync over.
    item = db.query(PlaidItem).filter(PlaidItem.item_id == item_id, PlaidItem.user_id == current_user.id).first()
    if item is None:
        item = PlaidItem(user_id=current_user.id, item_id=item_id)
        db.add(item)
    item.access_token = encryption.encrypt(access_token)
    item.institution_name = body.institution_name or item.institution_name
    item.cursor = None
    db.flush()

    for a in plaid_service.get_accounts(access_token):
        existing = (
            db.query(Account)
            .filter(Account.plaid_account_id == a["plaid_account_id"], Account.user_id == current_user.id)
            .first()
        )
        if existing:
            existing.current_balance = a["current_balance"]
            existing.plaid_item_id = item.id
        else:
            db.add(Account(user_id=current_user.id, plaid_item_id=item.id, **a))
    db.commit()

    sync_item(db, item)
    detection.run_detection(db, current_user.id)
    analytics.track(db, "bank_linked", current_user)

    return {"message": "Bank connected and transactions synced"}


@router.get("/items", response_model=list[PlaidItemResponse])
def list_items(current_user: User = Depends(require_real_user), db: Session = Depends(get_db)):
    """The banks this user has linked."""
    rows = (
        db.query(PlaidItem, func.count(Account.id))
        .outerjoin(Account, Account.plaid_item_id == PlaidItem.id)
        .filter(PlaidItem.user_id == current_user.id)
        .group_by(PlaidItem.id)
        .order_by(PlaidItem.created_at)
        .all()
    )
    return [
        PlaidItemResponse(
            id=item.id,
            institution_name=item.institution_name,
            account_count=count,
            last_synced_at=item.last_synced_at,
        )
        for item, count in rows
    ]


@router.post("/resync")
def resync(current_user: User = Depends(require_real_user), db: Session = Depends(get_db)):
    """Pull what changed at every linked bank since the last sync, then refresh
    subscriptions and alerts."""
    items = db.query(PlaidItem).filter(PlaidItem.user_id == current_user.id).all()
    if not items:
        raise HTTPException(status_code=400, detail="No bank account connected")

    touched = sum(sync_item(db, item) for item in items)
    detection.run_detection(db, current_user.id)
    analytics.track(db, "resync", current_user)

    return {"message": "Resynced", "transactions_touched": touched}
