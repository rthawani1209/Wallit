from datetime import date, timedelta

from app.models.subscription import Subscription
from app.models.transaction import Transaction
from app.services import detection

from .conftest import add_txn


def test_classify_interval_buckets():
    assert detection._classify_interval(7) == "weekly"
    assert detection._classify_interval(30.5) == "monthly"
    assert detection._classify_interval(91) == "quarterly"
    assert detection._classify_interval(365) == "annual"
    assert detection._classify_interval(14) is None


def test_project_occurrences_goes_backwards_and_forwards():
    sub = Subscription(billing_interval="monthly", next_estimated_date=date(2026, 6, 15))
    assert detection.project_occurrences(sub, date(2026, 3, 1), date(2026, 3, 31)) == [date(2026, 3, 17)]
    assert detection.project_occurrences(sub, date(2026, 6, 1), date(2026, 6, 30)) == [date(2026, 6, 15)]


def test_monthly_charge_becomes_subscription(db, user, account, categories):
    today = date.today()
    for months_ago in (3, 2, 1):
        add_txn(db, account, categories["Subscriptions"], 15.49, today - timedelta(days=30 * months_ago), "Netflix")

    detection.run_detection(db, user.id)

    sub = db.query(Subscription).filter_by(user_id=user.id, merchant_name="Netflix").one()
    assert sub.billing_interval == "monthly"
    assert sub.next_estimated_date >= today


def test_varying_grocery_runs_are_not_a_subscription(db, user, account, categories):
    today = date.today()
    for weeks_ago, amount in zip(range(8, 0, -1), (84, 131, 62, 140, 97, 55, 120, 73)):
        add_txn(db, account, categories["Food"], amount, today - timedelta(weeks=weeks_ago), "Trader Joe's")

    detection.run_detection(db, user.id)

    assert db.query(Subscription).filter_by(user_id=user.id).count() == 0


def test_dismissed_subscription_stays_dismissed(db, user, account, categories):
    today = date.today()
    for months_ago in (3, 2, 1):
        add_txn(db, account, categories["Health"], 40, today - timedelta(days=30 * months_ago), "City Gym")
    db.add(Subscription(user_id=user.id, merchant_name="City Gym", amount=40, billing_interval="monthly",
                        is_active=False, dismissed_by_user=True))
    db.flush()

    detection.run_detection(db, user.id)

    sub = db.query(Subscription).filter_by(user_id=user.id, merchant_name="City Gym").one()
    assert sub.is_active is False


def test_large_charge_flagged_as_anomaly(db, user, account, categories):
    today = date.today()
    for days_ago, amount in zip(range(170, 40, -15), (38, 42, 45, 40, 36, 44, 41, 39, 43)):
        add_txn(db, account, categories["Food"], amount, today - timedelta(days=days_ago), f"Diner {days_ago}")
    spike = add_txn(db, account, categories["Food"], 160, today - timedelta(days=3), "Steakhouse")

    detection.run_detection(db, user.id)

    db.refresh(spike)
    assert spike.is_anomaly
    assert "Food" in spike.anomaly_reason


def test_small_absolute_gap_is_not_an_anomaly(db, user, account, categories):
    today = date.today()
    for days_ago, amount in zip(range(170, 40, -15), (3, 3.5, 3.2, 2.9, 3.1, 3.4, 3, 3.3, 3.2)):
        add_txn(db, account, categories["Food"], amount, today - timedelta(days=days_ago), f"Coffee {days_ago}")
    coffee = add_txn(db, account, categories["Food"], 9, today - timedelta(days=2), "Fancy Coffee")

    detection.run_detection(db, user.id)

    db.refresh(coffee)
    assert not coffee.is_anomaly


def test_transfers_never_feed_anomaly_stats(db, user, account, categories):
    today = date.today()
    for days_ago in range(170, 40, -20):
        add_txn(db, account, categories["Transfer"], 50, today - timedelta(days=days_ago), "Transfer to Savings")
    big = add_txn(db, account, categories["Transfer"], 2000, today - timedelta(days=2), "Transfer to Savings")

    detection.run_detection(db, user.id)

    db.refresh(big)
    assert not big.is_anomaly
    assert db.query(Transaction).filter_by(account_id=account.id, is_anomaly=True).count() == 0
