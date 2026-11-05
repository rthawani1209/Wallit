from dataclasses import asdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.forecast import ForecastResponse
from app.services import analytics
from app.services.forecast import build_forecast

router = APIRouter(tags=["forecast"])


@router.get("/forecast", response_model=ForecastResponse)
def forecast(
    days: int = Query(30, ge=7, le=90, description="How far ahead to project"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Projected day-by-day balance and how much is safe to spend before payday."""
    result = asdict(build_forecast(db, current_user.id, horizon_days=days))
    analytics.track(db, "forecast_viewed", current_user)
    return result
