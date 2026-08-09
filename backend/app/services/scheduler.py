"""Re-runs subscription/anomaly detection for every linked user every 24 hours,
so a price hike or unusual charge gets flagged without a manual resync."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database import SessionLocal
from app.models.user import User
from app.services import detection

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def run_nightly_detection() -> None:
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.plaid_access_token.isnot(None)).all()
        logger.info("Nightly detection: running for %d user(s)", len(users))
        for user in users:
            detection.run_detection(db, user.id)
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler.add_job(
        run_nightly_detection,
        "interval",
        hours=24,
        id="nightly_detection",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
