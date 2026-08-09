"""
Tool-calling AI assistant. Answers general questions directly, and answers
questions about the user's own finances (transactions, spending, subscriptions,
bills, balances) by calling read-only tools backed by the user's real data —
never by guessing numbers. Also exposes a Google Places lookup so the assistant
can suggest cheaper food/entertainment options near the user.
"""
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
from app.services.detection import NON_DISCRETIONARY_CATEGORIES, project_occurrences
from app.services.places import search_places

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


# --- Tool implementations. Each takes (db, user, **params) and returns a JSON-able dict. ---


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


TOOL_HANDLERS = {
    "get_transactions": _tool_get_transactions,
    "get_spending_by_category": _tool_get_spending_by_category,
    "get_subscriptions_and_bills": _tool_get_subscriptions_and_bills,
    "get_upcoming_charges": _tool_get_upcoming_charges,
    "get_account_balances": _tool_get_account_balances,
    "get_spending_anomalies": _tool_get_spending_anomalies,
    "search_nearby_places": _tool_search_nearby_places,
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
        # Marks the end of the (identical-on-every-call) system+tools prefix as a cache
        # breakpoint — Anthropic caches everything up to here, so the tool loop's second+
        # call, and every later turn in the conversation, reads this ~1k-token block from
        # cache (~90% cheaper) instead of paying full price for it again.
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
        "You are not a licensed financial advisor: don't give personalized investment or trading advice "
        "(which stock/crypto to buy, market timing, etc.) — if asked, say so briefly and, if relevant, stick "
        "to what you can help with (budgeting, spending, subscriptions).\n\n"
        "Keep replies concise and conversational, like a sharp finance-savvy friend, not a report. Use plain "
        "text — short paragraphs and '- ' bullet lines when listing multiple items, **bold** around key "
        "numbers/merchants. No headers, no code blocks."
    )


def run_chat(db: Session, user: User, messages: list[dict]) -> str:
    """
    Runs the tool-calling loop against Claude and returns the final assistant
    reply text. `messages` is the full conversation so far (list of
    {"role": "user"|"assistant", "content": str}).
    """
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
            # Claude occasionally ends a turn with only an internal "thinking" block and
            # no visible text — nudge it to actually finish answering instead of dead-ending
            # the conversation on what the user experiences as a dropped question.
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
