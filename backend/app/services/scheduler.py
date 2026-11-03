"""Once a day, pulls what changed at every linked bank and re-runs
subscription/anomaly detection, so a price hike or unusual charge gets flagged
without the user pressing resync.

A fixed time of day rather than "every 24 hours": an interval timer restarts
on every deploy, and both hosts redeploy on each push to main, so an interval
job could go days without firing. It runs in a background thread so the
detection queries and Claude calls never block the API's event loop."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models.plaid_item import PlaidItem
from app.services import demo, detection
from app.services.item_sync import sync_item

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def run_nightly_detection() -> None:
    db = SessionLocal()
    try:
        items = db.query(PlaidItem).all()
        logger.info("Nightly sync: %d linked bank(s)", len(items))
        for item in items:
            item_id = item.id
            try:
                sync_item(db, item)
            except Exception:
                # One bank needing re-auth shouldn't stop everyone else's sync.
                db.rollback()
                logger.exception("Nightly sync failed for item %s", item_id)
        for user_id in {item.user_id for item in items}:
            detection.run_detection(db, user_id)
        removed = demo.delete_expired_demo_users(db)
        logger.info("Nightly cleanup: removed %d expired demo user(s)", removed)
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
