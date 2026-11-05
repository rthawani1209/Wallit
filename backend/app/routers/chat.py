import json
import logging
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import chat_events, run_chat
from app.services.demo import DEMO_CHAT_LIMIT
from app.services.rate_limit import chat_limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

MAX_MESSAGES = 40
DEMO_LIMIT_REPLY = (
    f"That's the {DEMO_CHAT_LIMIT}-message limit for a demo session, since every reply is a "
    "live Claude call. Sign up to keep going with your own data."
)

STREAM_ERROR_REPLY = "Sorry, something went wrong on our end. Please try again in a moment."


def _admit(body: ChatRequest, user: User, db: Session) -> list[dict] | None:
    """Validates the request and applies the limits. Returns the messages to send,
    or None when a demo user is out of messages."""
    if not body.messages:
        raise HTTPException(status_code=422, detail="messages must not be empty")
    if body.messages[-1].role != "user":
        raise HTTPException(status_code=422, detail="Last message must be from the user")

    if not chat_limiter.allow(str(user.id)):
        raise HTTPException(status_code=429, detail="You've sent a lot of messages this hour. Give it a little while.")

    if user.is_demo:
        if user.demo_chat_count >= DEMO_CHAT_LIMIT:
            return None
        user.demo_chat_count += 1
        db.commit()

    return [m.model_dump() for m in body.messages[-MAX_MESSAGES:]]


@router.post("", response_model=ChatResponse)
def post_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    messages = _admit(body, current_user, db)
    if messages is None:
        return ChatResponse(message=DEMO_LIMIT_REPLY)
    return ChatResponse(message=run_chat(db, current_user, messages))


def _sse(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"


@router.post("/stream")
def stream_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Same as POST /chat, but as server-sent events: a `tool` event each time the
    assistant looks something up, `text` events as the reply is written, then
    `done` with the full reply. Text streamed before a tool event was the
    assistant thinking out loud; the UI can fold it into the trace."""
    messages = _admit(body, current_user, db)
    user_id = current_user.id

    def events() -> Iterator[str]:
        # On this FastAPI version the get_db session is closed before a streaming
        # body runs. A closed Session reopens on first use, so close it again here
        # to hand the connection back once the reply is finished.
        # The client relies on every stream ending with `done`, so anything that
        # goes wrong here still sends one.
        try:
            if messages is None:
                yield _sse({"type": "done", "message": DEMO_LIMIT_REPLY})
                return
            user = db.get(User, user_id)
            if user is None:
                raise LookupError(f"user {user_id} disappeared mid-request")
            for event in chat_events(db, user, messages):
                yield _sse(event)
        except Exception:
            logger.exception("Chat stream failed")
            yield _sse({"type": "done", "message": STREAM_ERROR_REPLY})
        finally:
            db.close()

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        # Stop proxies (Vercel's rewrite included) from buffering the stream.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
