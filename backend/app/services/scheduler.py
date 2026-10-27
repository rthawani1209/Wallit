"""Re-runs subscription/anomaly detection for every linked user once a day, so a
price hike or unusual charge gets flagged without a manual resync.

A fixed time of day rather than "every 24 hours": an interval timer restarts
on every deploy, and both hosts redeploy on each push to main, so an interval
job could go days without firing. It runs in a background thread so the
detection queries and Claude calls never block the API's event loop."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models.user import User
from app.services import detection

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


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
        "cron",
        hour=9,  # 09:00 UTC, early morning in the US
        minute=0,
        id="nightly_detection",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    scheduler.shutdown(wait=False)
