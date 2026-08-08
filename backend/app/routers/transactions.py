from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transactions import CategorySpend, TransactionResponse, TransactionUpdateRequest

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _user_account_ids(db: Session, user_id) -> list:
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    return [a.id for a in accounts]


@router.get("", response_model=list[TransactionResponse])
def get_transactions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account_ids = _user_account_ids(db, current_user.id)
    return (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids))
        .order_by(Transaction.date.desc())
        .limit(100)
        .all()
    )


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: str,
    body: TransactionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually assign a category to a transaction (Phase 2 — precedes Phase 3's auto-categorization)."""
    account_ids = _user_account_ids(db, current_user.id)
    transaction = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id, Transaction.account_id.in_(account_ids))
        .first()
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    category = db.query(Category).filter(Category.id == body.category_id).first()
    if not category:
        raise HTTPException(status_code=400, detail="Invalid category")

    transaction.category_id = body.category_id
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/summary", response_model=list[CategorySpend])
def get_summary(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Spend by category, month-to-date. Only counts expenses (positive amounts), not income."""
    account_ids = _user_account_ids(db, current_user.id)
    month_start = date.today().replace(day=1)

    rows = (
        db.query(
            Category.id,
            Category.name,
            func.sum(Transaction.amount).label("total"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= month_start,
            Transaction.amount > 0,
        )
        .group_by(Category.id, Category.name)
        .all()
    )

    uncategorized_total = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= month_start,
            Transaction.amount > 0,
            Transaction.category_id.is_(None),
        )
        .scalar()
    )

    result = [
        CategorySpend(category_id=cat_id, category_name=name, total=float(total))
        for cat_id, name, total in rows
    ]
    if uncategorized_total:
        result.append(
            CategorySpend(category_id=None, category_name="Uncategorized", total=float(uncategorized_total))
        )
    return result
