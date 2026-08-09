"""
Budget progress computation and the set/upsert-a-limit action — shared by the
REST router (routers/budgets.py) and the chatbot's adjust_budget tool
(services/chat.py) so both write through the exact same logic.
"""
import uuid
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transactions import BudgetProgress


def _user_account_ids(db: Session, user_id) -> list:
    return [a.id for a in db.query(Account).filter(Account.user_id == user_id).all()]


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _shift_months(d: date, n: int) -> date:
    month_index = d.month - 1 + n
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _suggest_limit(avg_recent_spend: float) -> float:
    """Round up to the nearest $10, minimum $20 — an auto-suggested budget should
    leave some visible headroom rather than starting the user out already over."""
    if avg_recent_spend <= 0:
        return 20.0
    return max(20.0, ((avg_recent_spend // 10) + 1) * 10)


def get_budget_progress(db: Session, user: User) -> list[BudgetProgress]:
    """
    Budget vs actual spend for the current month, per category.

    A category only gets an entry here if it has a user-set limit, spend this
    month, or spend history to suggest a limit from — categories with no
    activity at all are omitted rather than shown as an empty 0/$20 bar.
    """
    account_ids = _user_account_ids(db, user.id)
    today = date.today()
    month_start = _month_start(today)
    history_start = _shift_months(month_start, -3)

    current_spend = dict(
        db.query(Transaction.category_id, func.sum(Transaction.amount))
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= month_start,
            Transaction.date <= today,
            Transaction.amount > 0,
        )
        .group_by(Transaction.category_id)
        .all()
    )

    months_with_data = (
        db.query(func.count(func.distinct(func.to_char(Transaction.date, "YYYY-MM"))))
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= history_start,
            Transaction.date < month_start,
        )
        .scalar()
    ) or 1

    history_rows = (
        db.query(Transaction.category_id, func.sum(Transaction.amount))
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= history_start,
            Transaction.date < month_start,
            Transaction.amount > 0,
        )
        .group_by(Transaction.category_id)
        .all()
    )
    avg_spend = {
        cat_id: float(total) / months_with_data for cat_id, total in history_rows if cat_id is not None
    }

    overrides = {
        b.category_id: b.monthly_limit for b in db.query(Budget).filter(Budget.user_id == user.id).all()
    }

    category_ids = set(current_spend) | set(avg_spend) | set(overrides)
    category_ids.discard(None)
    categories = {c.id: c.name for c in db.query(Category).filter(Category.id.in_(category_ids)).all()}

    result = []
    for cat_id in category_ids:
        spent = float(current_spend.get(cat_id) or 0)
        if cat_id in overrides:
            limit = float(overrides[cat_id])
            is_custom = True
        else:
            limit = _suggest_limit(avg_spend.get(cat_id, 0))
            is_custom = False
        result.append(
            BudgetProgress(
                category_id=cat_id,
                category_name=categories.get(cat_id, "Unknown"),
                limit=limit,
                spent=spent,
                is_custom=is_custom,
            )
        )
    result.sort(key=lambda b: (b.spent / b.limit) if b.limit else 0, reverse=True)
    return result


class BudgetUpsertError(Exception):
    """Raised for invalid input — the router maps this to a 400, the chat tool to an error dict."""


def upsert_budget(db: Session, user: User, category_id: uuid.UUID, limit: float) -> BudgetProgress:
    """Set (or update) a user's monthly limit for a category, returning the fresh progress."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise BudgetUpsertError("Invalid category")
    if limit <= 0:
        raise BudgetUpsertError("Limit must be positive")

    budget = db.query(Budget).filter(Budget.user_id == user.id, Budget.category_id == category_id).first()
    if budget:
        budget.monthly_limit = limit
    else:
        budget = Budget(user_id=user.id, category_id=category_id, monthly_limit=limit)
        db.add(budget)
    db.commit()

    account_ids = _user_account_ids(db, user.id)
    today = date.today()
    spent = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= _month_start(today),
            Transaction.date <= today,
            Transaction.amount > 0,
            Transaction.category_id == category_id,
        )
        .scalar()
    )

    return BudgetProgress(
        category_id=category.id,
        category_name=category.name,
        limit=float(limit),
        spent=float(spent or 0),
        is_custom=True,
    )
