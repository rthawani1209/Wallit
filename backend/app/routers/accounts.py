from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.account import Account
from app.models.user import User
from app.schemas.accounts import AccountResponse

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
def get_accounts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Account).filter(Account.user_id == current_user.id).all()
