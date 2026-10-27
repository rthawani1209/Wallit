"""Recruiter demo: a throwaway user with about eight months of realistic sample
data, so anyone can click through Wallit without an account or a bank.

Nothing about the analysis is faked. The sample transactions carry the same
Plaid-style category hints a real sync would, go through the same
save_transactions -> categorization -> detection path, and every chart,
subscription, price-hike flag and anomaly comes out of that real code.
Dates are generated relative to today so the demo never looks stale.
"""
import random
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services import detection
from app.services.transaction_sync import save_transactions

HISTORY_DAYS = 240
DEMO_TTL = timedelta(hours=24)
DEMO_CHAT_LIMIT = 20
MAX_LIVE_DEMO_USERS = 500

# Plaid personal_finance_category hints, as a real sync would hand them over.
PFC = {
    "income": ("INCOME", "INCOME_WAGES"),
    "rent": ("RENT_AND_UTILITIES", "RENT_AND_UTILITIES_RENT"),
    "power": ("RENT_AND_UTILITIES", "RENT_AND_UTILITIES_GAS_AND_ELECTRICITY"),
    "internet": ("RENT_AND_UTILITIES", "RENT_AND_UTILITIES_INTERNET_AND_CABLE"),
    "phone": ("RENT_AND_UTILITIES", "RENT_AND_UTILITIES_TELEPHONE"),
    "streaming": ("ENTERTAINMENT", "ENTERTAINMENT_TV_AND_MOVIES"),
    "music": ("ENTERTAINMENT", "ENTERTAINMENT_MUSIC_AND_AUDIO"),
    "events": ("ENTERTAINMENT", "ENTERTAINMENT_SPORTING_EVENTS_AMUSEMENT_PARKS_AND_MUSEUMS"),
    "cloud": ("GENERAL_SERVICES", "GENERAL_SERVICES_OTHER_GENERAL_SERVICES"),
    "gym": ("PERSONAL_CARE", "PERSONAL_CARE_GYMS_AND_FITNESS_CENTERS"),
    "groceries": ("FOOD_AND_DRINK", "FOOD_AND_DRINK_GROCERIES"),
    "coffee": ("FOOD_AND_DRINK", "FOOD_AND_DRINK_COFFEE"),
    "restaurant": ("FOOD_AND_DRINK", "FOOD_AND_DRINK_RESTAURANT"),
    "delivery": ("FOOD_AND_DRINK", "FOOD_AND_DRINK_FAST_FOOD"),
    "rideshare": ("TRANSPORTATION", "TRANSPORTATION_TAXIS_AND_RIDE_SHARES"),
    "gas": ("TRANSPORTATION", "TRANSPORTATION_GAS"),
    "shopping": ("GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_ONLINE_MARKETPLACES"),
    "store": ("GENERAL_MERCHANDISE", "GENERAL_MERCHANDISE_SUPERSTORES"),
    "pharmacy": ("MEDICAL", "MEDICAL_PHARMACIES_AND_SUPPLEMENTS"),
    "loan": ("LOAN_PAYMENTS", "LOAN_PAYMENTS_STUDENT_LOAN_PAYMENT"),
    "savings": ("TRANSFER_OUT", "TRANSFER_OUT_SAVINGS"),
    "venmo": ("TRANSFER_OUT", "TRANSFER_OUT_ACCOUNT_TRANSFER"),
    "donation": ("GOVERNMENT_AND_NON_PROFIT", "GOVERNMENT_AND_NON_PROFIT_DONATIONS"),
}

# Tips the real app would ask Claude for. Seeded so a demo visit costs nothing.
CHEAPER_ALTERNATIVES = {
    "Netflix": "The Standard with Ads plan is $7.99/mo and has the same catalog for most shows.",
    "Spotify": "Spotify Duo is $16.99/mo for two people, about $8.50 each if you split it.",
    "Crunch Fitness": "The Base membership is $12.99/mo if you only use one location.",
    "iCloud+": "Probably no better option at this price; 50GB is already the cheapest paid tier.",
    "Xfinity Internet": "Calling to ask for the current new-customer rate usually knocks $15-20/mo off.",
    "Mint Mobile": "Already one of the cheapest carriers; nothing obviously better.",
}


def _row(rng: random.Random, account: Account, on: date, merchant: str, amount: float, kind: str) -> dict:
    primary, detailed = PFC[kind]
    return {
        "plaid_transaction_id": f"demo-{uuid.UUID(int=rng.getrandbits(128))}",
        "amount": round(amount, 2),
        "merchant_name": merchant,
        "date": on,
        "plaid_account_id": account.plaid_account_id,
        "personal_finance_category": {"primary": primary, "detailed": detailed},
    }


def _monthly(start: date, end: date, day: int) -> list[date]:
    dates, year, month = [], start.year, start.month
    while True:
        d = date(year, month, min(day, 28))
        if d > end:
            return dates
        if d >= start:
            dates.append(d)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)


def _every(start: date, end: date, days: int, offset: int = 0) -> list[date]:
    d, dates = start + timedelta(days=offset), []
    while d <= end:
        dates.append(d)
        d += timedelta(days=days)
    return dates


def build_transactions(checking: Account, card: Account, today: date, seed: int = 7) -> tuple[list[dict], list[dict]]:
    """Returns (history, latest). `latest` holds the newest Netflix charge at a
    higher price, applied after a first detection pass so the price-hike check
    sees a real increase against the subscription it already knows."""
    rng = random.Random(seed)
    start = today - timedelta(days=HISTORY_DAYS)
    rows: list[dict] = []

    def add(account, on, merchant, amount, kind):
        rows.append(_row(rng, account, on, merchant, amount, kind))

    # Income and fixed bills, on checking. Plaid's sign convention: money in is negative.
    for d in _every(start, today, 14, offset=4):
        add(checking, d, "Northwind Labs Payroll", -2460.18, "income")
    for d in _monthly(start, today, 1):
        add(checking, d, "Maple Court Apartments", 1650.00, "rent")
    for d in _monthly(start, today, 3):
        add(checking, d, "Sallie Mae Student Loan", 287.40, "loan")
    for d in _monthly(start, today, 2):
        add(checking, d, "Transfer to High-Yield Savings", 500.00, "savings")
    for d in _monthly(start, today, 18):
        add(checking, d, "Seattle City Light", rng.uniform(58, 96), "power")

    # Subscriptions on the card. Netflix's last charge is held back (see docstring).
    for d in _monthly(start, today, 11):
        add(card, d, "Xfinity Internet", 75.00, "internet")
    for d in _monthly(start, today, 21):
        add(card, d, "Mint Mobile", 30.00, "phone")
    netflix_dates = _monthly(start, today, 14)
    for d in netflix_dates[:-1]:
        add(card, d, "Netflix", 15.49, "streaming")
    for d in _monthly(start, today, 6):
        add(card, d, "Spotify", 11.99, "music")
    for d in _monthly(start, today, 9):
        add(card, d, "iCloud+", 2.99, "cloud")
    for d in _monthly(start, today, 24):
        add(card, d, "Crunch Fitness", 29.99, "gym")

    # Variable day-to-day spending.
    for d in _every(start, today, 7, offset=1):
        add(card, d + timedelta(days=rng.randint(0, 2)), "Trader Joe's", rng.uniform(52, 128), "groceries")
    for d in _every(start, today, 1):
        if rng.random() < 0.35:
            add(card, d, "Starbucks", rng.uniform(4.75, 8.40), "coffee")
        if rng.random() < 0.12:
            add(card, d, rng.choice(["Chipotle", "Pho Bac", "Tacos Chukis"]), rng.uniform(11, 19), "restaurant")
        if rng.random() < 0.06:
            add(card, d, "DoorDash", rng.uniform(24, 46), "delivery")
        if rng.random() < 0.07:
            add(card, d, "Uber", rng.uniform(11, 31), "rideshare")
        if rng.random() < 0.09:
            add(card, d, "Amazon", rng.uniform(14, 95), "shopping")
    for d in _every(start, today, 10, offset=3):
        add(card, d, "Shell", rng.uniform(41, 58), "gas")
    for d in _every(start, today, 33, offset=8):
        add(card, d, "Target", rng.uniform(35, 110), "store")
    for d in _every(start, today, 18, offset=5):
        add(card, d, "AMC Theatres", rng.uniform(18, 32), "events")
    for d in _every(start, today, 45, offset=12):
        add(card, d, "Walgreens", rng.uniform(9, 34), "pharmacy")
    for d in _every(start, today, 26, offset=6):
        add(checking, d, "Venmo", rng.uniform(20, 85), "venmo")
    for d in _monthly(start, today, 27)[::3]:
        add(checking, d, "Northwest Harvest", 50.00, "donation")

    # A couple of genuinely unusual charges in the last month, for anomaly detection to find.
    add(card, today - timedelta(days=6), "Ticketmaster", 245.00, "events")
    add(card, today - timedelta(days=11), "Canlis", 212.60, "restaurant")

    latest = [_row(rng, card, netflix_dates[-1], "Netflix", 17.99, "streaming")]
    return rows, latest


def create_demo_user(db: Session) -> User:
    """Create and fully seed one demo user. Takes well under a second."""
    today = date.today()
    user = User(
        email=f"demo-{uuid.uuid4().hex[:12]}@demo.wallit.app",
        first_name="Alex",
        last_name="Rivera",
        is_demo=True,
    )
    db.add(user)
    db.flush()

    suffix = uuid.uuid4().hex[:10]
    checking = Account(user_id=user.id, plaid_account_id=f"demo-chk-{suffix}", name="Everyday Checking",
                       type="depository", current_balance=4821.37)
    card = Account(user_id=user.id, plaid_account_id=f"demo-card-{suffix}", name="Sapphire Credit Card",
                   type="credit", current_balance=1243.90)
    savings = Account(user_id=user.id, plaid_account_id=f"demo-sav-{suffix}", name="High-Yield Savings",
                      type="depository", current_balance=12460.00)
    db.add_all([checking, card, savings])
    db.flush()

    account_map = {a.plaid_account_id: a.id for a in (checking, card, savings)}
    category_map = {c.name: c.id for c in db.query(Category).all()}
    history, latest = build_transactions(checking, card, today, seed=int(suffix[:8], 16))

    save_transactions(db, account_map, category_map, history)
    db.flush()
    detection.run_detection(db, user.id, suggest_alternatives=False)
    save_transactions(db, account_map, category_map, latest)
    db.flush()
    detection.run_detection(db, user.id, suggest_alternatives=False)

    for sub in db.query(Subscription).filter(Subscription.user_id == user.id):
        sub.cheaper_alternative = CHEAPER_ALTERNATIVES.get(sub.merchant_name)

    created = datetime.now(timezone.utc)
    db.add_all(
        [
            Plan(user_id=user.id, type="trip", name="Japan Trip", target_amount=4500, monthly_contribution=375,
                 target_date=today + timedelta(days=300), location="Tokyo", created_at=created - timedelta(days=120)),
            Plan(user_id=user.id, type="savings_goal", name="Emergency Fund", target_amount=10000,
                 monthly_contribution=500, created_at=created - timedelta(days=200)),
        ]
    )
    db.add_all(
        [
            Budget(user_id=user.id, category_id=category_map["Food"], monthly_limit=650),
            Budget(user_id=user.id, category_id=category_map["Entertainment"], monthly_limit=120),
        ]
    )
    db.commit()
    db.refresh(user)
    return user


def is_expired(user: User) -> bool:
    return user.created_at is not None and datetime.now(timezone.utc) - user.created_at > DEMO_TTL


def evict_oldest_demo_users(db: Session, keep: int) -> int:
    """Delete the oldest demo users so at most `keep` remain."""
    total = db.query(User).filter(User.is_demo.is_(True)).count()
    if total <= keep:
        return 0
    oldest = (
        db.query(User)
        .filter(User.is_demo.is_(True))
        .order_by(User.created_at.asc())
        .limit(total - keep)
        .all()
    )
    for user in oldest:
        db.delete(user)
    db.commit()
    return len(oldest)


def delete_expired_demo_users(db: Session) -> int:
    """Remove demo users older than the TTL. ORM deletes so the cascades on
    User (accounts -> transactions, plans, budgets, subscriptions) apply."""
    cutoff = datetime.now(timezone.utc) - DEMO_TTL
    expired = db.query(User).filter(User.is_demo.is_(True), User.created_at < cutoff).all()
    for user in expired:
        db.delete(user)
    db.commit()
    return len(expired)
