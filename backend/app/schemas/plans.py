import uuid
from datetime import date, datetime

from pydantic import BaseModel


class PlanResponse(BaseModel):
    id: uuid.UUID
    type: str
    name: str
    target_amount: float
    target_date: date | None
    location: str | None
    monthly_contribution: float | None
    is_active: bool
    created_at: datetime

    # Computed, not stored — see services/plans.py:compute_progress
    saved_amount: float
    progress_pct: float
    is_achieved: bool
    projected_completion_date: date | None
    on_track: bool | None  # None when there's no target_date or no monthly_contribution to compare

    class Config:
        from_attributes = True


class PlanCreateRequest(BaseModel):
    name: str
    target_amount: float
    target_date: date | None = None
    monthly_contribution: float | None = None
    type: str = "savings_goal"
    location: str | None = None


class PlanUpdateRequest(BaseModel):
    name: str | None = None
    target_amount: float | None = None
    target_date: date | None = None
    monthly_contribution: float | None = None
    is_active: bool | None = None
