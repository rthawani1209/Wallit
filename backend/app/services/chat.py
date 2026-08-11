"""Tool-calling assistant. Answers questions about the user's own finances by
calling read-only tools backed by real data instead of guessing, and can
propose/apply budget and savings-goal changes once the user confirms."""
import json
import logging
from datetime import date, timedelta

import anthropic
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.account import Account
from app.models.category import Category
from app.models.subscription import Subscription
from app.models.transaction import Transaction
from app.models.user import User
from app.services.budgets import BudgetUpsertError, upsert_budget
from app.services.detection import NON_DISCRETIONARY_CATEGORIES, project_occurrences
from app.services.places import search_places
from app.services.plans import (
    PlanError,
    create_plan,
    find_plan_by_name,
    list_plans,
    to_response as plan_to_response,
    update_plan,
)

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-5"
MAX_TOOL_ITERATIONS = 8


def _user_account_ids(db: Session, user_id) -> list:
    return [a.id for a in db.query(Account).filter(Account.user_id == user_id).all()]


def _parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


# Tool implementations. Each takes (db, user, **params) and returns a JSON-able dict.


def _tool_get_transactions(db: Session, user: User, **params) -> dict:
    account_ids = _user_account_ids(db, user.id)
    today = date.today()
    start = _parse_date(params.get("start_date"), today.replace(month=1, day=1))
    end = _parse_date(params.get("end_date"), today)
    limit = min(int(params.get("limit") or 50), 200)

    query = (
        db.query(Transaction)
        .join(Category, Transaction.category_id == Category.id, isouter=True)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start,
            Transaction.date <= end,
        )
    )
    keyword = params.get("keyword")
    if keyword:
        query = query.filter(Transaction.merchant_name.ilike(f"%{keyword}%"))
    category = params.get("category")
    if category:
        query = query.filter(Category.name.ilike(category))

    all_matches = query.order_by(Transaction.date.desc()).all()
    total_amount = sum(float(t.amount) for t in all_matches)
    category_names = {c.id: c.name for c in db.query(Category).all()}

    return {
        "count": len(all_matches),
        "total_amount": round(total_amount, 2),
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "transactions": [
            {
                "date": t.date.isoformat(),
                "merchant_name": t.merchant_name,
                "amount": float(t.amount),
                "category_name": category_names.get(t.category_id),
            }
            for t in all_matches[:limit]
        ],
        "note": None
        if len(all_matches) <= limit
        else f"Showing the {limit} most recent of {len(all_matches)} matching transactions; count and total_amount cover all of them.",
    }


def _tool_get_spending_by_category(db: Session, user: User, **params) -> dict:
    account_ids = _user_account_ids(db, user.id)
    today = date.today()
    start = _parse_date(params.get("start_date"), today.replace(day=1))
    end = _parse_date(params.get("end_date"), today)

    rows = (
        db.query(Category.name, func.sum(Transaction.amount).label("total"))
        .join(Transaction, Transaction.category_id == Category.id)
        .filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.amount > 0,
            Category.name != "Transfer",
        )
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .all()
    )
    return {
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "by_category": [{"category_name": name, "total": round(float(total), 2)} for name, total in rows],
        "grand_total": round(sum(float(total) for _, total in rows), 2),
    }


def _tool_get_subscriptions_and_bills(db: Session, user: User, **params) -> dict:
    include_inactive = bool(params.get("include_inactive", False))
    query = db.query(Subscription).filter(Subscription.user_id == user.id)
    if not include_inactive:
        query = query.filter(Subscription.is_active.is_(True))
    subs = query.order_by(Subscription.next_estimated_date.asc().nulls_last()).all()
    category_names = {c.id: c.name for c in db.query(Category).all()}

    return {
        "subscriptions": [
            {
                "merchant_name": s.merchant_name,
                "amount": float(s.amount),
                "billing_interval": s.billing_interval,
                "next_estimated_date": s.next_estimated_date.isoformat() if s.next_estimated_date else None,
                "category_name": category_names.get(s.category_id),
                "is_discretionary_subscription": category_names.get(s.category_id) not in NON_DISCRETIONARY_CATEGORIES,
                "cheaper_alternative": s.cheaper_alternative,
                "is_active": s.is_active,
            }
            for s in subs
        ]
    }


def _tool_get_upcoming_charges(db: Session, user: User, **params) -> dict:
    month = params.get("month") or date.today().strftime("%Y-%m")
    try:
        year, month_num = (int(p) for p in month.split("-"))
        range_start = date(year, month_num, 1)
    except (ValueError, IndexError):
        range_start = date.today().replace(day=1)
        month = range_start.strftime("%Y-%m")
    next_month = date(range_start.year + (range_start.month == 12), (range_start.month % 12) + 1, 1)
    range_end = next_month - timedelta(days=1)

    subs = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.is_active.is_(True))
        .all()
    )
    category_names = {c.id: c.name for c in db.query(Category).all()}

    events = []
    for sub in subs:
        for occurrence_date in project_occurrences(sub, range_start, range_end):
            events.append(
                {
                    "date": occurrence_date.isoformat(),
                    "merchant_name": sub.merchant_name,
                    "amount": float(sub.amount),
                    "category_name": category_names.get(sub.category_id),
                }
            )
    events.sort(key=lambda e: e["date"])
    return {
        "month": month,
        "total_due": round(sum(e["amount"] for e in events), 2),
        "charges": events,
    }


def _tool_get_account_balances(db: Session, user: User, **params) -> dict:
    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    return {
        "accounts": [
            {
                "name": a.name,
                "type": a.type,
                "balance": float(a.current_balance) if a.current_balance is not None else None,
            }
            for a in accounts
        ]
    }


def _tool_get_spending_anomalies(db: Session, user: User, **params) -> dict:
    account_ids = _user_account_ids(db, user.id)
    category_names = {c.id: c.name for c in db.query(Category).all()}
    txns = (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids), Transaction.is_anomaly.is_(True))
        .order_by(Transaction.date.desc())
        .limit(20)
        .all()
    )
    return {
        "anomalies": [
            {
                "date": t.date.isoformat(),
                "merchant_name": t.merchant_name,
                "amount": float(t.amount),
                "category_name": category_names.get(t.category_id),
                "reason": t.anomaly_reason,
            }
            for t in txns
        ]
    }


def _tool_search_nearby_places(db: Session, user: User, **params) -> dict:
    query = params.get("query")
    location = params.get("location")
    if not query or not location:
        return {"error": "Both query and location are required."}
    return search_places(query=query, location=location, max_results=int(params.get("max_results") or 5))


def _tool_check_affordability(db: Session, user: User, **params) -> dict:
    amount = params.get("amount")
    if not amount or amount <= 0:
        return {"error": "amount must be a positive number"}

    accounts = db.query(Account).filter(Account.user_id == user.id).all()
    current_balance = sum(float(a.current_balance) for a in accounts if a.current_balance is not None)

    subs = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.is_active.is_(True))
        .all()
    )
    today = date.today()
    window_end = today + timedelta(days=30)
    upcoming_committed = sum(
        float(sub.amount) * len(project_occurrences(sub, today, window_end)) for sub in subs
    )

    goals = list_plans(db, user)
    monthly_goal_commitment = sum(float(g.monthly_contribution) for g in goals if g.monthly_contribution)

    buffer_after = round(current_balance - upcoming_committed - monthly_goal_commitment - amount, 2)

    return {
        "purchase_amount": amount,
        "current_balance": round(current_balance, 2),
        "upcoming_committed_next_30_days": round(upcoming_committed, 2),
        "active_savings_goal_monthly_commitments": round(monthly_goal_commitment, 2),
        "buffer_after_purchase": buffer_after,
        "note": (
            "buffer_after_purchase is what's left after this purchase, the next 30 days of bills/"
            "subscriptions, and this month's pledged savings-goal contributions. Negative means this "
            "purchase would eat into money already committed elsewhere."
        ),
    }


def _tool_get_savings_goals(db: Session, user: User, **params) -> dict:
    include_inactive = bool(params.get("include_inactive", False))
    goals = list_plans(db, user, include_inactive=include_inactive)
    return {"goals": [plan_to_response(g).model_dump(mode="json") for g in goals]}


def _tool_create_savings_goal(db: Session, user: User, **params) -> dict:
    name = params.get("name")
    target_amount = params.get("target_amount")
    if not name or not target_amount:
        return {"error": "name and target_amount are required"}

    target_date = None
    if params.get("target_date"):
        try:
            target_date = date.fromisoformat(params["target_date"])
        except ValueError:
            return {"error": "target_date must be YYYY-MM-DD"}

    try:
        plan = create_plan(
            db,
            user,
            name=name,
            target_amount=target_amount,
            target_date=target_date,
            monthly_contribution=params.get("monthly_contribution"),
        )
    except PlanError as e:
        return {"error": str(e)}
    return plan_to_response(plan).model_dump(mode="json")


def _tool_update_savings_goal(db: Session, user: User, **params) -> dict:
    name = params.get("name")
    if not name:
        return {"error": "name is required to find the goal"}
    plan = find_plan_by_name(db, user, name)
    if not plan:
        return {"error": f"No active savings goal matching {name!r}."}

    fields = {}
    if params.get("target_amount") is not None:
        fields["target_amount"] = params["target_amount"]
    if params.get("monthly_contribution") is not None:
        fields["monthly_contribution"] = params["monthly_contribution"]
    if params.get("target_date"):
        try:
            fields["target_date"] = date.fromisoformat(params["target_date"])
        except ValueError:
            return {"error": "target_date must be YYYY-MM-DD"}
    if params.get("mark_complete_or_cancel"):
        fields["is_active"] = False

    try:
        plan = update_plan(db, user, plan.id, **fields)
    except PlanError as e:
        return {"error": str(e)}
    return plan_to_response(plan).model_dump(mode="json")


def _tool_adjust_budget(db: Session, user: User, **params) -> dict:
    category_name = params.get("category_name")
    new_monthly_limit = params.get("new_monthly_limit")
    if not category_name or not new_monthly_limit:
        return {"error": "category_name and new_monthly_limit are required"}

    category = db.query(Category).filter(Category.name.ilike(category_name)).first()
    if not category:
        valid = ", ".join(sorted(c.name for c in db.query(Category).all()))
        return {"error": f"No category named {category_name!r}. Valid categories: {valid}"}

    try:
        progress = upsert_budget(db, user, category.id, new_monthly_limit)
    except BudgetUpsertError as e:
        return {"error": str(e)}
    return progress.model_dump(mode="json")


def _tool_dismiss_subscription(db: Session, user: User, **params) -> dict:
    merchant_name = params.get("merchant_name")
    if not merchant_name:
        return {"error": "merchant_name is required"}

    sub = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.merchant_name.ilike(f"%{merchant_name}%"))
        .first()
    )
    if not sub:
        return {"error": f"No detected subscription/recurring charge matching {merchant_name!r}."}

    sub.is_active = False
    sub.dismissed_by_user = True
    db.commit()
    return {
        "merchant_name": sub.merchant_name,
        "dismissed": True,
        "note": (
            "This merchant will no longer be treated as a subscription or shown on the calendar, "
            "even if it keeps recurring with a consistent amount/interval."
        ),
    }


def _tool_recategorize_transactions(db: Session, user: User, **params) -> dict:
    keyword = params.get("keyword")
    new_category_name = params.get("new_category_name")
    if not keyword or not new_category_name:
        return {"error": "keyword and new_category_name are required"}

    category = db.query(Category).filter(Category.name.ilike(new_category_name)).first()
    if not category:
        valid = ", ".join(sorted(c.name for c in db.query(Category).all()))
        return {"error": f"No category named {new_category_name!r}. Valid categories: {valid}"}

    account_ids = _user_account_ids(db, user.id)
    txns = (
        db.query(Transaction)
        .filter(Transaction.account_id.in_(account_ids), Transaction.merchant_name.ilike(f"%{keyword}%"))
        .all()
    )
    if not txns:
        return {"error": f"No transactions matching {keyword!r} found."}

    for t in txns:
        t.category_id = category.id
        t.category_is_manual = True
    db.commit()
    return {
        "matched_count": len(txns),
        "new_category": category.name,
        "note": "Marked as a manual override, so a future bank sync won't revert these back to the auto-resolved category.",
    }


TOOL_HANDLERS = {
    "get_transactions": _tool_get_transactions,
    "get_spending_by_category": _tool_get_spending_by_category,
    "get_subscriptions_and_bills": _tool_get_subscriptions_and_bills,
    "get_upcoming_charges": _tool_get_upcoming_charges,
    "get_account_balances": _tool_get_account_balances,
    "get_spending_anomalies": _tool_get_spending_anomalies,
    "search_nearby_places": _tool_search_nearby_places,
    "check_affordability": _tool_check_affordability,
    "get_savings_goals": _tool_get_savings_goals,
    "create_savings_goal": _tool_create_savings_goal,
    "update_savings_goal": _tool_update_savings_goal,
    "adjust_budget": _tool_adjust_budget,
    "dismiss_subscription": _tool_dismiss_subscription,
    "recategorize_transactions": _tool_recategorize_transactions,
}

TOOL_DEFINITIONS = [
    {
        "name": "get_transactions",
        "description": (
            "Search the user's real transaction history. Use this for any question about specific "
            "purchases or spend on a merchant/keyword (e.g. 'how much did I spend on golf this year', "
            "'what was that Uber charge', 'show me my Starbucks purchases'). Always returns an exact "
            "total_amount and count computed over ALL matching transactions, not just the ones listed — "
            "use that number rather than adding up the listed rows yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD, inclusive. Defaults to Jan 1 of the current year."},
                "end_date": {"type": "string", "description": "YYYY-MM-DD, inclusive. Defaults to today."},
                "keyword": {"type": "string", "description": "Case-insensitive substring match on merchant name, e.g. 'golf', 'uber', 'starbucks'."},
                "category": {"type": "string", "description": "Exact category name, e.g. 'Food', 'Entertainment', 'Transportation'."},
                "limit": {"type": "integer", "description": "Max transactions to return in the list (default 50, max 200). count/total_amount always cover the full match set."},
            },
        },
    },
    {
        "name": "get_spending_by_category",
        "description": "Total spend broken down by category for a date range. Use for 'what did I spend by category this month/year' style questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "YYYY-MM-DD, inclusive. Defaults to the 1st of the current month."},
                "end_date": {"type": "string", "description": "YYYY-MM-DD, inclusive. Defaults to today."},
            },
        },
    },
    {
        "name": "get_subscriptions_and_bills",
        "description": "List the user's detected recurring subscriptions and bills, with amount, billing interval, next due date, category, and any known cheaper alternative.",
        "input_schema": {
            "type": "object",
            "properties": {
                "include_inactive": {"type": "boolean", "description": "Include subscriptions no longer detected as active. Default false."},
            },
        },
    },
    {
        "name": "get_upcoming_charges",
        "description": "Every bill/subscription charge projected to occur in a given calendar month (past, current, or future). Use for 'what's due this month/next month/in December' questions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "YYYY-MM. Defaults to the current month."},
            },
        },
    },
    {
        "name": "get_account_balances",
        "description": "The user's linked accounts (checking, credit card, etc.) with current balance.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_spending_anomalies",
        "description": "Transactions already flagged as unusual — either abnormally large for their category, or a subscription price increase.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "check_affordability",
        "description": (
            "Check whether the user can afford a specific one-time purchase, weighing it against their "
            "current balance, upcoming bills/subscriptions in the next 30 days, and any money already "
            "pledged toward active savings goals. Use for 'can I afford X' / 'should I buy X' questions — "
            "never estimate this yourself, always call the tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "The purchase price to check."},
                "description": {"type": "string", "description": "What the purchase is, for context in your answer."},
            },
            "required": ["amount"],
        },
    },
    {
        "name": "get_savings_goals",
        "description": (
            "List the user's savings goals (e.g. a trip fund) with computed progress: saved_amount, "
            "progress_pct, is_achieved, whether it's on_track for its target_date, and "
            "projected_completion_date at the current pace."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "include_inactive": {"type": "boolean", "description": "Include archived/cancelled goals. Default false."},
            },
        },
    },
    {
        "name": "create_savings_goal",
        "description": (
            "Create a new savings goal (e.g. a trip fund). WRITE ACTION — only call this after you've "
            "already told the user, in a prior message, the specific name/target_amount/"
            "monthly_contribution you're about to set up, and they've confirmed. Never call this in the "
            "same turn you first propose the numbers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "e.g. 'Japan Trip'"},
                "target_amount": {"type": "number"},
                "target_date": {"type": "string", "description": "YYYY-MM-DD, optional — when they want to reach the goal by."},
                "monthly_contribution": {"type": "number", "description": "How much to pledge toward this goal per month, optional."},
            },
            "required": ["name", "target_amount"],
        },
    },
    {
        "name": "update_savings_goal",
        "description": (
            "Adjust an existing savings goal's target, monthly contribution, or target date, or archive it "
            "(mark_complete_or_cancel) once achieved or abandoned. WRITE ACTION — same confirm-first rule "
            "as create_savings_goal: propose the change, wait for the user to confirm, then call this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name (or partial name) of the existing goal to update."},
                "target_amount": {"type": "number"},
                "monthly_contribution": {"type": "number"},
                "target_date": {"type": "string", "description": "YYYY-MM-DD"},
                "mark_complete_or_cancel": {"type": "boolean", "description": "Set true to archive this goal (achieved or no longer wanted)."},
            },
            "required": ["name"],
        },
    },
    {
        "name": "adjust_budget",
        "description": (
            "Set a user's monthly spending limit for a category (their existing Budgets feature, shown on "
            "the dashboard). WRITE ACTION — only call this after proposing the exact category and new "
            "limit in a prior message and the user has confirmed. Never call this in the same turn you "
            "first propose the numbers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category_name": {"type": "string", "description": "Exact category name, e.g. 'Food', 'Entertainment', 'Transportation'."},
                "new_monthly_limit": {"type": "number"},
            },
            "required": ["category_name", "new_monthly_limit"],
        },
    },
    {
        "name": "dismiss_subscription",
        "description": (
            "Permanently stop treating a merchant as a detected subscription/recurring bill — e.g. the "
            "user says 'that's not really a subscription, I just buy from them every week' or 'remove this "
            "from my calendar'. This is different from a normal cancellation: it just fixes a misdetection, "
            "so the merchant will never be re-flagged as recurring again even if it keeps showing the same "
            "amount/interval. WRITE ACTION — confirm with the user which merchant before calling this, "
            "unless they already named it explicitly (e.g. 'remove Trader Joe's from my subscriptions')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "merchant_name": {"type": "string", "description": "Merchant name (or partial match) as it appears in their transactions/subscriptions."},
            },
            "required": ["merchant_name"],
        },
    },
    {
        "name": "recategorize_transactions",
        "description": (
            "Bulk-fix the category of every transaction matching a merchant/keyword — use when the user "
            "says a merchant's category is wrong (e.g. 'that Amazon charge was actually Shopping not Food' "
            "or 'put all my Uber charges under Transportation'). Marks them as a manual override so a future "
            "bank sync won't silently revert the fix. WRITE ACTION — describe which transactions and the new "
            "category in a prior message and get the user's confirmation before calling this."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "Case-insensitive substring match on merchant name, e.g. 'amazon', 'uber'."},
                "new_category_name": {"type": "string", "description": "Exact category name to assign, e.g. 'Food', 'Shopping', 'Transfer'."},
            },
            "required": ["keyword", "new_category_name"],
        },
    },
    {
        "name": "search_nearby_places",
        "description": (
            "Search Google Places for cheaper food/entertainment/errand options near a location, sorted "
            "cheapest first. Use when the user asks for cheaper places to eat, things to do, or 'X near me'. "
            "Requires a location — if the user hasn't said where they are (city, neighborhood, or zip), ask "
            "them before calling this tool rather than guessing."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for, e.g. 'cheap tacos', 'movie theater', 'coffee shop'."},
                "location": {"type": "string", "description": "City, neighborhood, zip code, or address to search near."},
                "max_results": {"type": "integer", "description": "Max results to return, default 5."},
            },
            "required": ["query", "location"],
        },
        # cache breakpoint — system+tools is identical on every call, so cache it
        "cache_control": {"type": "ephemeral"},
    },
]


def _system_prompt() -> str:
    today = date.today()
    return (
        "You are the Wallit Assistant, a modern AI financial assistant built into the Wallit personal "
        f"finance app. Today's date is {today.isoformat()}.\n\n"
        "You can hold normal conversation, and you have tools that give you real, live access to the "
        "current user's own linked accounts, transactions, subscriptions, bills, and spending anomalies. "
        "Whenever a question is about the user's own money — a specific merchant, a spending total, "
        "'this year'/'last month'/'last week', a balance, an upcoming bill, a subscription, or 'what did I "
        "spend on X' — you MUST call the relevant tool and answer using the real numbers it returns. Never "
        "guess or estimate a number about the user's finances. Compute relative date ranges ('this year', "
        "'last month') yourself from today's date and pass explicit start_date/end_date to the tools.\n\n"
        "For 'cheaper places to eat/go' questions, use search_nearby_places — ask the user for their "
        "location first if they haven't given one.\n\n"
        "For 'can I afford X' / 'should I buy X' questions, use check_affordability rather than eyeballing "
        "a balance — it already accounts for upcoming bills and savings-goal commitments.\n\n"
        "You can also set up and manage savings goals (create_savings_goal, update_savings_goal, "
        "get_savings_goals) and adjust category budget limits (adjust_budget) — e.g. helping someone free "
        "up money each month toward a trip by trimming other categories. You can also fix data the app got "
        "wrong: dismiss_subscription permanently un-flags a merchant that was wrongly detected as a "
        "recurring subscription (e.g. a weekly grocery run at the same store), and "
        "recategorize_transactions bulk-fixes the category for every transaction matching a merchant/"
        "keyword. These six are WRITE actions with a hard rule, no exceptions even if the user says "
        "something like 'just do it, no need to ask': describe exactly what you're about to change in your "
        "reply first (which merchant, which category, which transactions matched, the effect) and ask the "
        "user to confirm — do NOT call the write tool in that same turn. Only call it after the user's next "
        "message clearly confirms (e.g. 'yes', 'do it', 'sounds good'). This matters especially for "
        "recategorize_transactions, since its keyword match is a substring search that can catch more "
        "merchants than intended (e.g. 'uber' also matches 'Uber Eats') — say what actually matched before "
        "applying it. get_savings_goals and check_affordability are read-only — call those freely, no "
        "confirmation needed. When proposing budget cuts, first call "
        "get_spending_by_category and get_subscriptions_and_bills so the categories/amounts you suggest are "
        "grounded in what the user actually spends, not guessed.\n\n"
        "Money moving between the user's own accounts (an internal transfer) is filed under the 'Transfer' "
        "category and excluded from spending/income totals — if a large amount shows up as both a "
        "TRANSFER_IN and TRANSFER_OUT-style charge, that's normal and not a real gain or loss.\n\n"
        "You are not a licensed financial advisor: don't give personalized investment or trading advice "
        "(which stock/crypto to buy, market timing, etc.) — if asked, say so briefly and, if relevant, stick "
        "to what you can help with (budgeting, spending, subscriptions).\n\n"
        "Keep replies concise and conversational, like a sharp finance-savvy friend, not a report. Use plain "
        "text — short paragraphs and '- ' bullet lines when listing multiple items, **bold** around key "
        "numbers/merchants. No headers, no code blocks."
    )


def run_chat(db: Session, user: User, messages: list[dict]) -> str:
    """Runs the tool-calling loop and returns the final reply text. `messages` is
    the full conversation so far (list of {"role": ..., "content": str})."""
    if not settings.anthropic_api_key:
        return "The AI assistant isn't configured on this server (missing Anthropic API key)."

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    conversation: list[dict] = [{"role": m["role"], "content": m["content"]} for m in messages]

    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=[{"type": "text", "text": _system_prompt()}],
                tools=TOOL_DEFINITIONS,
                messages=conversation,
            )
        except Exception:
            logger.exception("Claude chat call failed")
            return "Sorry, I hit an error talking to the AI service. Please try again in a moment."

        if response.stop_reason != "tool_use":
            text = "".join(block.text for block in response.content if block.type == "text").strip()
            if text:
                return text
            # sometimes ends a turn with only a thinking block and no text — nudge it to finish
            conversation.append({"role": "assistant", "content": response.content})
            conversation.append({"role": "user", "content": "Please give your answer now."})
            continue

        conversation.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            handler = TOOL_HANDLERS.get(block.name)
            try:
                result = handler(db, user, **block.input) if handler else {"error": f"Unknown tool {block.name}"}
            except Exception:
                logger.exception("Tool %s failed with input %r", block.name, block.input)
                result = {"error": "This tool failed to run."}
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
            )
        conversation.append({"role": "user", "content": tool_results})

    return "That took more steps than expected — could you narrow down the question a bit?"
