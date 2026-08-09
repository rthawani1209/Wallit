import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transactions import SimulateResponse

router = APIRouter(tags=["simulate"])


@router.get("/simulate", response_model=SimulateResponse)
def simulate(
    percent_change: float = Query(
        ..., ge=-100, description="e.g. -20 to cut spend by 20%, 15 to increase by 15%. Can't go below -100 (can't spend less than $0)."
    ),
    category_id: uuid.UUID | None = Query(None, description="Limit the change to one category; omit for total spend"),
    start_date: date | None = Query(None, description="Defaults to the 1st of the current month"),
    end_date: date | None = Query(None, description="Defaults to today"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """What-if simulator — apply a hypothetical % change to one category or total
    spend and project the resulting balance."""
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    account_ids = [a.id for a in accounts]
    current_balance = float(sum(a.current_balance or 0 for a in accounts))

    range_start = start_date or date.today().replace(day=1)
    range_end = end_date or date.today()
    base_filters = [
        Transaction.account_id.in_(account_ids),
        Transaction.date >= range_start,
        Transaction.date <= range_end,
        Transaction.amount > 0,
    ]
    if category_id is not None:
        base_filters.append(Transaction.category_id == category_id)

    actual_spend = float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(*base_filters).scalar()
    )

    if category_id is not None:
        delta = actual_spend * (percent_change / 100)
        projected_spend = actual_spend + delta
    else:
        projected_spend = actual_spend * (1 + percent_change / 100)
        delta = projected_spend - actual_spend

    return SimulateResponse(
        current_balance=round(current_balance, 2),
        actual_spend=round(actual_spend, 2),
        projected_spend=round(projected_spend, 2),
        projected_balance=round(current_balance - delta, 2),
    )
