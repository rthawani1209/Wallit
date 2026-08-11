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
PRICE_HIKE_THRESHOLD = 1.05  # 5%

# Transfers/paychecks aren't charges at all. NON_DISCRETIONARY_CATEGORIES is a
# looser filter used by the Subscriptions page to hide bills, not by detection itself.
NON_RECURRING_CHARGE_CATEGORIES = {"Savings", "Income", "Transfer"}
NON_DISCRETIONARY_CATEGORIES = {"Debt", "Housing", "Savings", "Income", "Transfer"}

INTERVAL_DAYS = {"weekly": 7, "monthly": 30, "quarterly": 91, "annual": 365}


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


def project_occurrences(sub: Subscription, range_start: date, range_end: date) -> list[date]:
    """Occurrence dates for `sub` within [range_start, range_end], in either direction."""
    step = INTERVAL_DAYS.get(sub.billing_interval)
    if not step or not sub.next_estimated_date:
        return []

    d = sub.next_estimated_date
    while d > range_start:
        d -= timedelta(days=step)
    while d < range_start:
        d += timedelta(days=step)

    occurrences = []
    while d <= range_end:
        occurrences.append(d)
        d += timedelta(days=step)
    return occurrences


def suggest_cheaper_alternative(merchant_name: str, amount: float, billing_interval: str) -> str | None:
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
            Category.name.notin_(NON_RECURRING_CHARGE_CATEGORIES),
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
        existing = existing_subs.get(merchant)
        if existing and existing.dismissed_by_user:
            continue
        amounts = [float(t.amount) for t in occurrences]
        # Need a 3+ point stable baseline before treating the newest charge as a price
        # hike rather than just amount drift (e.g. a usage-based utility bill).
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
        latest_category_id = occurrences[-1].category_id
        sub = existing_subs.get(merchant)
        if sub:
            old_amount = float(sub.amount)
            sub.amount = latest_amount
            sub.billing_interval = interval_label
            sub.next_estimated_date = next_due
            sub.category_id = latest_category_id
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
                    category_id=latest_category_id,
                    is_active=True,
                    cheaper_alternative=suggest_cheaper_alternative(merchant, latest_amount, interval_label),
                )
            )

    for merchant, sub in existing_subs.items():
        if merchant not in seen_merchants and sub.is_active:
            sub.is_active = False


def detect_category_anomalies(db: Session, user_id) -> None:
    from app.models.account import Account
    from app.models.category import Category

    account_ids = [a.id for a in db.query(Account).filter(Account.user_id == user_id).all()]
    if not account_ids:
        return

    today = date.today()
    recent_start = today - timedelta(days=ANOMALY_RECENT_DAYS)
    history_start = today - timedelta(days=ANOMALY_HISTORY_DAYS)

    transfer_category_id = (
        db.query(Category.id).filter(Category.name == "Transfer").scalar()
    )

    history_rows = (
        db.query(Transaction.category_id, Transaction.amount)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= history_start,
            Transaction.date < recent_start,
            Transaction.amount > 0,
            Transaction.category_id.isnot(None),
            Transaction.category_id != transfer_category_id,
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
        if t.is_anomaly or t.category_id not in stats:
            continue
        mean, stddev = stats[t.category_id]
        amount = float(t.amount)
        if amount > mean + ANOMALY_STDDEV_MULTIPLIER * stddev and amount > mean + ANOMALY_MIN_DOLLAR_GAP:
            pct = round((amount / mean - 1) * 100)
            cat_name = category_names.get(t.category_id, "this category")
            t.is_anomaly = True
            t.anomaly_reason = f"{pct}% higher than your typical {cat_name} spend (avg ${mean:.2f})"


def run_detection(db: Session, user_id) -> None:
    """Run both passes for one user. Best-effort — a bad run never propagates."""
    try:
        detect_subscriptions(db, user_id)
        detect_category_anomalies(db, user_id)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Detection run failed for user %s", user_id)
