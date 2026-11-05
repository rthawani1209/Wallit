"""Cash-flow forecast and the "safe to spend" number.

The projection starts from spendable cash today (checking-type accounts, minus
what's owed on credit cards), then walks forward one day at a time:
- recurring charges land on their projected dates (detected subscriptions,
  which include rent and loan payments),
- paychecks land on theirs (recurring deposits in the Income category), and so
  do recurring transfers out to savings,
- everything else is spread evenly as the average daily variable spend of the
  last 60 days, or of however much history there is if the bank was linked
  more recently (history_days says which).

Safe to spend is the lowest the balance gets before the next paycheck: you
could spend that much extra today and still not go below zero by payday."""
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import median

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.subscription import Subscription
from app.models.transaction import Transaction
from app.services.detection import project_occurrences

VARIABLE_LOOKBACK_DAYS = 60
# A bank linked yesterday shouldn't have one coffee averaged over a single day.
MIN_HISTORY_DAYS = 14
INCOME_LOOKBACK_DAYS = 120
MIN_PAYCHECKS = 3
# Recurring transfers and pay aren't spending, so they stay out of the daily average.
NOT_SPENDING = {"Transfer", "Savings", "Income"}


@dataclass
class Event:
    name: str
    amount: float  # positive = money out, negative = money in (Plaid's convention)


@dataclass
class Day:
    date: date
    balance: float
    events: list[Event] = field(default_factory=list)


@dataclass
class Forecast:
    starting_balance: float
    daily_variable_spend: float
    # How many days of history the daily spend is averaged over. Under 60 means
    # the account is new and the estimate is rougher.
    history_days: int
    days: list[Day]
    next_payday: date | None
    safe_to_spend: float
    low_point: Day


def _is_spendable(account: Account) -> bool:
    # Plaid gives checking and savings the same type; we don't store the subtype,
    # so savings accounts are recognized by name.
    return account.type == "depository" and "saving" not in (account.name or "").lower()


def starting_balance(accounts: list[Account]) -> float:
    cash = sum(float(a.current_balance or 0) for a in accounts if _is_spendable(a))
    owed = sum(float(a.current_balance or 0) for a in accounts if a.type == "credit")
    return round(cash - owed, 2)


def project_recurring(txns_in: list[Transaction], start: date, end: date) -> list[tuple[date, str, float]]:
    """Future dates for each source that has moved money on a steady schedule
    (an employer's paychecks, an automatic savings transfer)."""
    by_source: dict[str, list[Transaction]] = defaultdict(list)
    for t in txns_in:
        by_source[t.merchant_name or "Unknown"].append(t)

    projected = []
    for source, txns in by_source.items():
        txns.sort(key=lambda t: t.date)
        if len(txns) < MIN_PAYCHECKS:
            continue
        gaps = [(b.date - a.date).days for a, b in zip(txns, txns[1:])]
        step = round(median(gaps))
        # weekly through monthly, and every gap close to the usual one
        if not 6 <= step <= 32 or any(abs(g - step) > 3 for g in gaps):
            continue
        amount = median(float(t.amount) for t in txns[-3:])
        d = txns[-1].date + timedelta(days=step)
        while d < start:
            d += timedelta(days=step)
        while d <= end:
            projected.append((d, source, amount))
            d += timedelta(days=step)
    return projected


def build_forecast(db: Session, user_id, horizon_days: int = 30, today: date | None = None) -> Forecast:
    today = today or date.today()
    end = today + timedelta(days=horizon_days)
    accounts = db.query(Account).filter(Account.user_id == user_id).all()
    account_ids = [a.id for a in accounts]
    balance = starting_balance(accounts)

    subs = (
        db.query(Subscription)
        .filter(Subscription.user_id == user_id, Subscription.is_active.is_(True), Subscription.dismissed_by_user.is_(False))
        .all()
    )
    events: dict[date, list[Event]] = defaultdict(list)
    for sub in subs:
        for d in project_occurrences(sub, today + timedelta(days=1), end):
            events[d].append(Event(sub.merchant_name, float(sub.amount)))

    category_names = {c.id: c.name for c in db.query(Category).all()}
    recent = (
        db.query(Transaction)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date > today - timedelta(days=max(VARIABLE_LOOKBACK_DAYS, INCOME_LOOKBACK_DAYS)),
            Transaction.date <= today,
        )
        .all()
        if account_ids
        else []
    )

    deposits = [
        t for t in recent
        if float(t.amount) < 0
        and category_names.get(t.category_id) == "Income"
        and t.date > today - timedelta(days=INCOME_LOOKBACK_DAYS)
    ]
    paychecks = project_recurring(deposits, today + timedelta(days=1), end)
    for d, source, amount in paychecks:
        events[d].append(Event(source, amount))

    to_savings = [
        t for t in recent
        if float(t.amount) > 0
        and category_names.get(t.category_id) == "Savings"
        and t.date > today - timedelta(days=INCOME_LOOKBACK_DAYS)
    ]
    for d, source, amount in project_recurring(to_savings, today + timedelta(days=1), end):
        events[d].append(Event(source, amount))

    # Day-to-day spending: everything that isn't a recurring charge, pay or a transfer.
    recurring = {s.merchant_name for s in subs}
    variable_total = sum(
        float(t.amount)
        for t in recent
        if float(t.amount) > 0
        and t.date > today - timedelta(days=VARIABLE_LOOKBACK_DAYS)
        and t.merchant_name not in recurring
        and category_names.get(t.category_id) not in NOT_SPENDING
    )
    # Divide by the days we actually have. Dividing a new account's two weeks of
    # spending by 60 would understate it 4x and overstate safe to spend.
    window_start = today - timedelta(days=VARIABLE_LOOKBACK_DAYS)
    earliest = min((t.date for t in recent if t.date > window_start), default=today)
    history_days = min(VARIABLE_LOOKBACK_DAYS, max(MIN_HISTORY_DAYS, (today - earliest).days + 1))
    daily_variable = round(variable_total / history_days, 2)

    days = []
    for i in range(1, horizon_days + 1):
        d = today + timedelta(days=i)
        balance -= daily_variable
        balance -= sum(e.amount for e in events[d])
        days.append(Day(d, round(balance, 2), sorted(events[d], key=lambda e: -e.amount)))

    next_payday = min((d for d, _, _ in paychecks), default=None)
    # Count payday itself as before the money arrives: bills due that morning still
    # have to clear on what's there.
    before_pay = [day for day in days if next_payday is None or day.date < next_payday]
    if next_payday is not None:
        payday = next(day for day in days if day.date == next_payday)
        pay_in = sum(-e.amount for e in payday.events if e.amount < 0)
        before_pay.append(Day(payday.date, round(payday.balance - pay_in, 2), payday.events))
    window = before_pay or days
    low = min(window, key=lambda day: day.balance)

    return Forecast(
        starting_balance=round(starting_balance(accounts), 2),
        daily_variable_spend=daily_variable,
        history_days=history_days,
        days=days,
        next_payday=next_payday,
        safe_to_spend=max(0.0, low.balance),
        low_point=low,
    )
