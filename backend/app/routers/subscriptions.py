from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscriptions import SubscriptionResponse

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("", response_model=list[SubscriptionResponse])
def get_subscriptions(
    include_inactive: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detected recurring charges, soonest due first. Populated by detection.run_detection,
    which runs automatically after every Plaid sync/resync and on the nightly schedule."""
    query = db.query(Subscription).filter(Subscription.user_id == current_user.id)
    if not include_inactive:
        query = query.filter(Subscription.is_active.is_(True))
    return query.order_by(Subscription.next_estimated_date.asc().nulls_last()).all()
