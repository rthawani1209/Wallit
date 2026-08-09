"""Savings-goal (Plan) CRUD and progress computation, shared by routers/plans.py
and the chatbot's goal tools. Progress is a pledged-pace estimate
(monthly_contribution x months elapsed) rather than a ledger of verified
transfers, since there's no real "moved to savings" signal to track against."""
import uuid
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.plan import Plan
from app.models.user import User
from app.schemas.plans import PlanResponse

DAYS_PER_MONTH = 30.44  # smooths progress day-to-day instead of only at month boundaries


class PlanError(Exception):
    """Raised for invalid input — the router maps this to a 400/404, the chat tool to an error dict."""


def _months_elapsed(start: date, end: date) -> float:
    return max(0.0, (end - start).days / DAYS_PER_MONTH)


def compute_progress(plan: Plan) -> dict:
    target = float(plan.target_amount)
    contribution = float(plan.monthly_contribution) if plan.monthly_contribution else 0.0

    elapsed_months = _months_elapsed(plan.created_at.date(), date.today())
    saved_amount = min(target, contribution * elapsed_months) if contribution > 0 else 0.0
    progress_pct = round((saved_amount / target) * 100, 1) if target > 0 else 0.0
    is_achieved = target > 0 and saved_amount >= target

    projected_completion_date = None
    on_track = None
    if contribution > 0 and target > 0:
        months_needed = target / contribution
        projected_completion_date = plan.created_at.date() + timedelta(days=months_needed * DAYS_PER_MONTH)
        if plan.target_date:
            on_track = projected_completion_date <= plan.target_date

    return {
        "saved_amount": round(saved_amount, 2),
        "progress_pct": progress_pct,
        "is_achieved": is_achieved,
        "projected_completion_date": projected_completion_date,
        "on_track": on_track,
    }


def to_response(plan: Plan) -> PlanResponse:
    progress = compute_progress(plan)
    return PlanResponse(
        id=plan.id,
        type=plan.type,
        name=plan.name,
        target_amount=float(plan.target_amount),
        target_date=plan.target_date,
        location=plan.location,
        monthly_contribution=float(plan.monthly_contribution) if plan.monthly_contribution else None,
        is_active=plan.is_active,
        created_at=plan.created_at,
        **progress,
    )


def list_plans(db: Session, user: User, include_inactive: bool = False) -> list[Plan]:
    query = db.query(Plan).filter(Plan.user_id == user.id)
    if not include_inactive:
        query = query.filter(Plan.is_active.is_(True))
    return query.order_by(Plan.created_at.desc()).all()


def get_plan(db: Session, user: User, plan_id: uuid.UUID) -> Plan:
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.user_id == user.id).first()
    if not plan:
        raise PlanError("Goal not found")
    return plan


def create_plan(
    db: Session,
    user: User,
    name: str,
    target_amount: float,
    target_date: date | None = None,
    monthly_contribution: float | None = None,
    type: str = "savings_goal",
    location: str | None = None,
) -> Plan:
    if target_amount <= 0:
        raise PlanError("target_amount must be positive")
    if monthly_contribution is not None and monthly_contribution <= 0:
        raise PlanError("monthly_contribution must be positive")

    plan = Plan(
        user_id=user.id,
        type=type,
        name=name,
        target_amount=target_amount,
        target_date=target_date,
        monthly_contribution=monthly_contribution,
        location=location,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_plan(db: Session, user: User, plan_id: uuid.UUID, **fields) -> Plan:
    plan = get_plan(db, user, plan_id)
    for key, value in fields.items():
        if value is None:
            continue
        if key in ("target_amount", "monthly_contribution") and value <= 0:
            raise PlanError(f"{key} must be positive")
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


def find_plan_by_name(db: Session, user: User, name: str) -> Plan | None:
    """Loose lookup for the chatbot, which knows a goal's name, not its id."""
    return (
        db.query(Plan)
        .filter(Plan.user_id == user.id, Plan.is_active.is_(True), Plan.name.ilike(f"%{name}%"))
        .first()
    )
