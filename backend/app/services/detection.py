"""
Subscription and anomaly detection, run after every Plaid sync and on a nightly
schedule (see app/services/scheduler.py). Two independent passes:

  1. Subscription detection — find merchants that recur at a consistent amount and
     cadence, persist them as Subscription rows, flag their transactions, and detect
     price increases on subscriptions we already knew about.
  2. Category anomaly detection — flag individual transactions that are unusually
     large relative to the user's own recent history in that category.

Both are best-effort: a failure in one user's detection (e.g. a Claude API outage)
must never block another user's, and is always caught by the caller.
"""
import logging
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models.transaction import Transaction
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)

SUBSCRIPTION_LOOKBACK_DAYS = 180
ANOMALY_RECENT_DAYS = 30
ANOMALY_HISTORY_DAYS = 180
MIN_HISTORY_SAMPLES = 4
ANOMALY_STDDEV_MULTIPLIER = 2
ANOMALY_MIN_DOLLAR_GAP = 20
PRICE_HIKE_THRESHOLD = 1.05  # 5% increase

NON_SUBSCRIPTION_CATEGORIES = {"Debt", "Savings", "Housing", "Income"}


def _classify_interval(avg_days: float) -> str | None:
    if 5 <= avg_days <= 9:
        return "weekly"
    if 24 <= avg_days <= 36:
        return "monthly"
    if 80 <= avg_days <= 100:
        return "quarterly"
    if 350 <= avg_days <= 380:
        return "annual"
    return None


def suggest_cheaper_alternative(merchant_name: str, amount: float, billing_interval: str) -> str | None:
    """
    Ask Claude for one concise money-saving suggestion for a recurring charge.
    Never raises — returns None on any failure so a Claude outage can't break detection.
    """
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=60,
            system=(
                "You are a personal-finance assistant. Given a recurring subscription or bill, "
                "suggest ONE concise, realistic way to save money on it — a cheaper tier, a "
                "well-known competitor, a bundling trick, or say there's likely no better option "
                "if that's genuinely true. One short sentence. No preamble, no markdown."
            ),
            messages=[{"role": "user", "content": f"{merchant_name}, ${amount:.2f}/{billing_interval}"}],
        )
        text = message.content[0].text.strip()
        return text or None
    except Exception:
        logger.exception("Claude cheaper-alternative suggestion failed for %r", merchant_name)
        return None


def detect_subscriptions(db: Session, user_id) -> None:
    """
    Group recent transactions by merchant, identify ones recurring at a consistent
    amount and cadence, and upsert a Subscription row for each. Flags matching
    transactions as is_subscription, and flags a price-hike anomaly when an existing
    subscription's amount jumps by more than 5%.
    """
    from app.models.account import Account
    from app.models.category import Category

    account_ids = [a.id for a in db.query(Account).filter(Account.user_id == user_id).all()]
    if not account_ids:
        return

    lookback_start = date.today() - timedelta(days=SUBSCRIPTION_LOOKBACK_DAYS)
    txns = (
        db.query(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= lookback_start,
            Transaction.amount > 0,
            Transaction.merchant_name.isnot(None),
            # Recurring debt payments, savings transfers, rent, and income aren't
            # "subscriptions" a user would think to cancel or downgrade — they're
            # already visible elsewhere (Upcoming Bills, the Savings category).
            Category.name.notin_(NON_SUBSCRIPTION_CATEGORIES),
        )
        .order_by(Transaction.date)
        .all()
    )

    by_merchant: dict[str, list[Transaction]] = defaultdict(list)
    for t in txns:
        by_merchant[t.merchant_name].append(t)

    existing_subs = {
        s.merchant_name: s for s in db.query(Subscription).filter(Subscription.user_id == user_id).all()
    }
    seen_merchants: set[str] = set()
    today = date.today()

    for merchant, occurrences in by_merchant.items():
        if len(occurrences) < 2:
            continue
        amounts = [float(t.amount) for t in occurrences]
        # A real subscription price hike has a specific shape: a tightly consistent
        # baseline of at least 3 prior charges, then ONE newer charge that jumped.
        # Requiring 3+ baseline points (not 2) matters: a 2-point baseline is too easy
        # to satisfy by chance for something that's just drifting continuously (e.g. a
        # utility bill creeping up with usage/season) rather than genuinely a stable
        # price that changed once. Below that, fall back to requiring every amount —
        # baseline and latest alike — to be tightly consistent together.
        if len(amounts) >= 4:
            baseline, latest = amounts[:-1], amounts[-1]
            baseline_avg = sum(baseline) / len(baseline)
            baseline_consistent = all(abs(a - baseline_avg) <= baseline_avg * 0.15 + 1 for a in baseline)
            latest_consistent = baseline_avg > 0 and abs(latest - baseline_avg) <= baseline_avg * 0.6
            if not (baseline_consistent and latest_consistent):
                continue
        else:
            avg_amount = sum(amounts) / len(amounts)
            if any(abs(a - avg_amount) > avg_amount * 0.15 + 1 for a in amounts):
                continue

        intervals = [
            (occurrences[i].date - occurrences[i - 1].date).days for i in range(1, len(occurrences))
        ]
        avg_interval = sum(intervals) / len(intervals)
        interval_label = _classify_interval(avg_interval)
        if not interval_label:
            continue

        seen_merchants.add(merchant)
        next_due = occurrences[-1].date + timedelta(days=round(avg_interval))
        while next_due < today:
            next_due += timedelta(days=round(avg_interval))

        for t in occurrences:
            t.is_subscription = True

        latest_amount = amounts[-1]
        sub = existing_subs.get(merchant)
        if sub:
            old_amount = float(sub.amount)
            sub.amount = latest_amount
            sub.billing_interval = interval_label
            sub.next_estimated_date = next_due
            sub.is_active = True
            if old_amount > 0 and latest_amount > old_amount * PRICE_HIKE_THRESHOLD:
                latest_txn = occurrences[-1]
                latest_txn.is_anomaly = True
                latest_txn.anomaly_reason = (
                    f"{merchant} price increased from ${old_amount:.2f} to ${latest_amount:.2f}"
                )
                sub.cheaper_alternative = suggest_cheaper_alternative(
                    merchant, latest_amount, interval_label
                )
        else:
            db.add(
                Subscription(
                    user_id=user_id,
                    merchant_name=merchant,
                    amount=latest_amount,
                    billing_interval=interval_label,
                    next_estimated_date=next_due,
                    is_active=True,
                    cheaper_alternative=suggest_cheaper_alternative(merchant, latest_amount, interval_label),
                )
            )

    # A merchant that used to recur but hasn't shown up in this window anymore —
    # keep the row (and its cheaper-alternative history) but mark it inactive.
    for merchant, sub in existing_subs.items():
        if merchant not in seen_merchants and sub.is_active:
            sub.is_active = False


def detect_category_anomalies(db: Session, user_id) -> None:
    """
    Flag recent transactions that are statistical outliers relative to the user's own
    trailing spend in that category — e.g. a much-larger-than-usual grocery run.
    """
    from app.models.account import Account
    from app.models.category import Category

    account_ids = [a.id for a in db.query(Account).filter(Account.user_id == user_id).all()]
    if not account_ids:
        return

    today = date.today()
    recent_start = today - timedelta(days=ANOMALY_RECENT_DAYS)
    history_start = today - timedelta(days=ANOMALY_HISTORY_DAYS)

    history_rows = (
        db.query(Transaction.category_id, Transaction.amount)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= history_start,
            Transaction.date < recent_start,
            Transaction.amount > 0,
            Transaction.category_id.isnot(None),
        )
        .all()
    )
    by_category: dict = defaultdict(list)
    for cat_id, amount in history_rows:
        by_category[cat_id].append(float(amount))

    stats: dict = {}
    for cat_id, amounts in by_category.items():
        if len(amounts) < MIN_HISTORY_SAMPLES:
            continue
        mean = sum(amounts) / len(amounts)
        variance = sum((a - mean) ** 2 for a in amounts) / len(amounts)
        stats[cat_id] = (mean, variance**0.5)

    recent_txns = (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= recent_start,
            Transaction.amount > 0,
        )
        .all()
    )

    category_names = {c.id: c.name for c in db.query(Category).all()}

    for t in recent_txns:
        if t.is_anomaly:
            continue  # already flagged (e.g. by a subscription price hike)
        if t.category_id not in stats:
            continue
        mean, stddev = stats[t.category_id]
        amount = float(t.amount)
        if amount > mean + ANOMALY_STDDEV_MULTIPLIER * stddev and amount > mean + ANOMALY_MIN_DOLLAR_GAP:
            pct = round((amount / mean - 1) * 100)
            cat_name = category_names.get(t.category_id, "this category")
            t.is_anomaly = True
            t.anomaly_reason = f"{pct}% higher than your typical {cat_name} spend (avg ${mean:.2f})"


def run_detection(db: Session, user_id) -> None:
    """Run both detection passes for one user and commit. Never raises."""
    try:
        detect_subscriptions(db, user_id)
        detect_category_anomalies(db, user_id)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Detection run failed for user %s", user_id)
