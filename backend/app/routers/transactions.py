import uuid
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transactions import (
    CashFlowMonth,
    CategorySpend,
    TransactionResponse,
    TransactionUpdateRequest,
    UpcomingBill,
)
from app.schemas.subscriptions import AnomalyResponse

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
    transaction_id: uuid.UUID,
    body: TransactionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually assign a category to a transaction. Marked as a manual override so a
    later Plaid resync never silently reverts it back to the auto-resolved category."""
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
    transaction.category_is_manual = True
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


# Categories that represent fixed recurring obligations rather than variable day-to-day
# spend — a merchant that happens to repeat monthly (e.g. a regular coffee run) shouldn't
# show up as a "bill" just because the amount and cadence look consistent.
BILL_LIKE_CATEGORIES = {"Subscriptions", "Utilities", "Housing", "Debt"}


@router.get("/upcoming-bills", response_model=list[UpcomingBill])
def get_upcoming_bills(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Detects recurring monthly charges from transaction history and predicts each
    one's next due date, so there's no separate bill-entry step."""
    account_ids = _user_account_ids(db, current_user.id)
    lookback_start = date.today() - timedelta(days=120)

    txns = (
        db.query(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= lookback_start,
            Transaction.amount > 0,
            Transaction.merchant_name.isnot(None),
            Category.name.in_(BILL_LIKE_CATEGORIES),
        )
        .order_by(Transaction.date)
        .all()
    )

    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for t in txns:
        by_merchant[t.merchant_name].append(t)

    today = date.today()
    bills = []
    for merchant, occurrences in by_merchant.items():
        if len(occurrences) < 2:
            continue
        amounts = [float(t.amount) for t in occurrences]
        avg_amount = sum(amounts) / len(amounts)
        # Wildly inconsistent amounts mean this is a repeat purchase, not a fixed bill.
        if any(abs(a - avg_amount) > avg_amount * 0.15 + 1 for a in amounts):
            continue

        intervals = [
            (occurrences[i].date - occurrences[i - 1].date).days for i in range(1, len(occurrences))
        ]
        avg_interval = sum(intervals) / len(intervals)
        # Only a roughly-monthly cadence counts as a recurring bill here.
        if not (24 <= avg_interval <= 36):
            continue

        next_due = occurrences[-1].date + timedelta(days=round(avg_interval))
        while next_due < today:
            next_due += timedelta(days=round(avg_interval))
        if next_due > today + timedelta(days=45):
            continue

        bills.append(UpcomingBill(merchant_name=merchant, amount=round(avg_amount, 2), next_due_date=next_due))

    bills.sort(key=lambda b: b.next_due_date)
    return bills[:8]


@router.get("/anomalies", response_model=list[AnomalyResponse])
def get_anomalies(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Recent transactions flagged by detection.run_detection — unusually large for
    their category, or a subscription price increase."""
    account_ids = _user_account_ids(db, current_user.id)
    category_names = {c.id: c.name for c in db.query(Category).all()}

    txns = (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids), Transaction.is_anomaly.is_(True))
        .order_by(Transaction.date.desc())
        .limit(20)
        .all()
    )
    return [
        AnomalyResponse(
            id=t.id,
            merchant_name=t.merchant_name,
            amount=float(t.amount),
            date=t.date,
            category_name=category_names.get(t.category_id),
            anomaly_reason=t.anomaly_reason,
        )
        for t in txns
    ]
