from datetime import date, timedelta

import pytest

from app.models.account import Account
from app.models.subscription import Subscription
from app.services import demo
from app.services.forecast import build_forecast, starting_balance

from tests.conftest import add_txn

TODAY = date(2026, 11, 4)


@pytest.fixture
def card(db, user):
    c = Account(user_id=user.id, plaid_account_id="card-1", name="Visa", type="credit", current_balance=500)
    db.add(c)
    db.flush()
    return c


def test_starting_balance_is_checking_minus_card_debt(db, user, account, card):
    savings = Account(user_id=user.id, plaid_account_id="sav-1", name="High-Yield Savings", type="depository",
                      current_balance=9000)
    db.add(savings)
    db.flush()
    # checking 2500 - card 500; savings isn't spending money
    assert starting_balance([account, card, savings]) == 2000


def test_bills_paychecks_and_daily_spend_add_up(db, user, account, card, categories):
    # paid every 14 days, last on Oct 30, so next payday is Nov 13
    for weeks_back in range(4):
        add_txn(db, account, categories["Income"], -2000, date(2026, 10, 30) - timedelta(days=14 * weeks_back),
                merchant="Acme Payroll")
    # rent of 1200 due Nov 10
    db.add(Subscription(user_id=user.id, merchant_name="Landlord", amount=1200, billing_interval="monthly",
                        next_estimated_date=date(2026, 11, 10), is_active=True))
    # $600 of groceries over the last 60 days = $10 a day
    for i in range(6):
        add_txn(db, account, categories["Food"], 100, TODAY - timedelta(days=4 + i * 11), merchant="Market")
    # a transfer to savings is not spending
    add_txn(db, account, categories["Transfer"], 400, TODAY - timedelta(days=3), merchant="To savings")
    db.flush()

    f = build_forecast(db, user.id, horizon_days=30, today=TODAY)

    assert f.starting_balance == 2000
    assert f.daily_variable_spend == 10
    assert f.history_days == 60
    assert f.next_payday == date(2026, 11, 13)
    by_day = {d.date: d for d in f.days}
    assert by_day[date(2026, 11, 10)].balance == 2000 - 6 * 10 - 1200
    # lowest point is the morning of payday: 9 days of spend and the rent
    assert f.safe_to_spend == 2000 - 9 * 10 - 1200
    assert f.low_point.date == date(2026, 11, 13)
    # after pay lands the balance climbs back
    assert by_day[date(2026, 11, 13)].balance == 2000 - 9 * 10 - 1200 + 2000


def test_no_paycheck_means_the_whole_window_counts(db, user, account, categories):
    db.add(Subscription(user_id=user.id, merchant_name="Gym", amount=40, billing_interval="monthly",
                        next_estimated_date=TODAY + timedelta(days=20), is_active=True))
    db.flush()

    f = build_forecast(db, user.id, horizon_days=30, today=TODAY)

    assert f.next_payday is None
    assert f.safe_to_spend == 2500 - 40


def test_irregular_deposits_are_not_treated_as_pay(db, user, account, categories):
    for days_back in (3, 20, 24, 61):
        add_txn(db, account, categories["Income"], -300, TODAY - timedelta(days=days_back), merchant="Side gig")
    db.flush()
    assert build_forecast(db, user.id, today=TODAY).next_payday is None


def test_new_account_averages_over_the_history_it_has(db, user, account, categories):
    # linked 20 days ago: $400 of spending is $20 a day, not $400 / 60
    for i in range(20):
        add_txn(db, account, categories["Food"], 20, TODAY - timedelta(days=i), merchant="Market")
    db.flush()

    f = build_forecast(db, user.id, horizon_days=30, today=TODAY)

    assert f.history_days == 20
    assert f.daily_variable_spend == 20
    assert f.safe_to_spend == 2500 - 30 * 20


def test_a_few_days_of_history_uses_the_floor(db, user, account, categories):
    add_txn(db, account, categories["Food"], 70, TODAY - timedelta(days=1), merchant="Market")
    db.flush()

    f = build_forecast(db, user.id, horizon_days=30, today=TODAY)

    assert f.history_days == 14
    assert f.daily_variable_spend == 5


def test_demo_forecast_is_sensible(db):
    user = demo.create_demo_user(db)
    f = build_forecast(db, user.id)

    # checking 4,821.37 minus the card's 1,243.90; savings left out
    assert f.starting_balance == pytest.approx(3577.47)
    assert f.next_payday is not None and (f.next_payday - date.today()).days <= 14
    assert 0 < f.safe_to_spend < f.starting_balance
    names = [e.name for d in f.days for e in d.events]
    assert names.count("Maple Court Apartments") == 1
    # the automatic $500 savings transfer leaves checking too
    assert names.count("Transfer to High-Yield Savings") == 1
