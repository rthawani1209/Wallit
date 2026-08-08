from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transactions import CashFlowMonth, CategorySpend, TransactionResponse, TransactionUpdateRequest

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
def get_summary(
    start_date: date | None = Query(None, description="Defaults to the 1st of the current month"),
    end_date: date | None = Query(None, description="Defaults to today"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Spend by category for a date range (defaults to month-to-date). Only counts expenses, not income."""
    account_ids = _user_account_ids(db, current_user.id)
    range_start = start_date or date.today().replace(day=1)
    range_end = end_date or date.today()

    rows = (
        db.query(
            Category.id,
            Category.name,
            func.sum(Transaction.amount).label("total"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= range_start,
            Transaction.date <= range_end,
            Transaction.amount > 0,
        )
        .group_by(Category.id, Category.name)
        .all()
    )

    uncategorized_total = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= range_start,
            Transaction.date <= range_end,
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


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _shift_months(d: date, n: int) -> date:
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


@router.get("/cashflow", response_model=list[CashFlowMonth])
def get_cashflow(
    months: int = Query(7, ge=1, le=24),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Income vs expenses per month, for the trailing N months (Plaid convention: amount < 0 is money in)."""
    account_ids = _user_account_ids(db, current_user.id)
    range_start = _shift_months(_month_start(date.today()), -(months - 1))

    month_key = func.to_char(Transaction.date, "YYYY-MM")
    rows = (
        db.query(
            month_key.label("month"),
            func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)).label("income"),
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label("expenses"),
        )
        .filter(Transaction.account_id.in_(account_ids), Transaction.date >= range_start)
        .group_by(month_key)
        .all()
    )
    by_month = {r.month: r for r in rows}

    result = []
    for i in range(months):
        month_date = _shift_months(range_start, i)
        key = month_date.strftime("%Y-%m")
        row = by_month.get(key)
        result.append(
            CashFlowMonth(
                month=key,
                label=month_date.strftime("%b"),
                income=float(row.income) if row else 0.0,
                expenses=float(row.expenses) if row else 0.0,
            )
        )
    return result
