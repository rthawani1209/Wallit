from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import run_chat
from app.services.demo import DEMO_CHAT_LIMIT

router = APIRouter(prefix="/chat", tags=["chat"])

MAX_MESSAGES = 40


@router.post("", response_model=ChatResponse)
def post_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.messages:
        raise HTTPException(status_code=422, detail="messages must not be empty")
    if body.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="Last message must be from the user")

    if current_user.is_demo:
        if current_user.demo_chat_count >= DEMO_CHAT_LIMIT:
            return ChatResponse(
                message=(
                    f"That's the {DEMO_CHAT_LIMIT}-message limit for a demo session, since every reply is a "
                    "live Claude call. Sign up to keep going with your own data."
                )
            )
        current_user.demo_chat_count += 1
        db.commit()

    messages = [m.model_dump() for m in body.messages[-MAX_MESSAGES:]]
    reply = run_chat(db, current_user, messages)
    return ChatResponse(message=reply)
