import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.transactions import BudgetProgress, BudgetSetRequest
from app.services.budgets import BudgetUpsertError, get_budget_progress, upsert_budget

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.get("/progress", response_model=list[BudgetProgress])
def get_progress(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_budget_progress(db, current_user)


@router.put("/{category_id}", response_model=BudgetProgress)
def set_budget(
    category_id: uuid.UUID,
    body: BudgetSetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set (or update) a user's monthly limit for a category — the 'Manage' flow."""
    try:
        return upsert_budget(db, current_user, category_id, body.limit)
    except BudgetUpsertError as e:
        raise HTTPException(status_code=400, detail=str(e))
