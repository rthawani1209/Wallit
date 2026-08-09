import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.plans import PlanCreateRequest, PlanResponse, PlanUpdateRequest
from app.services.plans import PlanError, create_plan, list_plans, to_response, update_plan

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("", response_model=list[PlanResponse])
def get_plans(
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [to_response(p) for p in list_plans(db, current_user, include_inactive)]


@router.post("", response_model=PlanResponse)
def post_plan(
    body: PlanCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        plan = create_plan(
            db,
            current_user,
            name=body.name,
            target_amount=body.target_amount,
            target_date=body.target_date,
            monthly_contribution=body.monthly_contribution,
            type=body.type,
            location=body.location,
        )
    except PlanError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return to_response(plan)


@router.patch("/{plan_id}", response_model=PlanResponse)
def patch_plan(
    plan_id: uuid.UUID,
    body: PlanUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        plan = update_plan(db, current_user, plan_id, **body.model_dump(exclude_unset=True))
    except PlanError as e:
        status_code = 404 if str(e) == "Goal not found" else 400
        raise HTTPException(status_code=status_code, detail=str(e))
    return to_response(plan)
