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
    percent_change: float = Query(..., description="e.g. -20 to cut spend by 20%, 15 to increase by 15%"),
    category_id: uuid.UUID | None = Query(None, description="Limit the change to one category; omit for total spend"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    What-if budget simulator: apply a hypothetical percent change to either one category's
    month-to-date spend or total month-to-date spend, and project the resulting balance.
    """
    accounts = db.query(Account).filter(Account.user_id == current_user.id).all()
    account_ids = [a.id for a in accounts]
    current_balance = float(sum(a.current_balance or 0 for a in accounts))

    month_start = date.today().replace(day=1)
    base_filters = [
        Transaction.account_id.in_(account_ids),
        Transaction.date >= month_start,
        Transaction.amount > 0,
    ]
    if category_id is not None:
        base_filters.append(Transaction.category_id == category_id)

    actual_month_spend = float(
        db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(*base_filters).scalar()
    )

    if category_id is not None:
        delta = actual_month_spend * (percent_change / 100)
        projected_month_spend = actual_month_spend + delta
    else:
        projected_month_spend = actual_month_spend * (1 + percent_change / 100)
        delta = projected_month_spend - actual_month_spend

    return SimulateResponse(
        current_balance=current_balance,
        actual_month_spend=actual_month_spend,
        projected_month_spend=projected_month_spend,
        projected_balance=current_balance - delta,
    )
