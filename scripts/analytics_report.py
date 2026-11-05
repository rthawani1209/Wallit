"""Print Wallit's usage numbers as Markdown.

    DATABASE_URL=<Railway's public Postgres URL> JWT_SECRET_KEY=unused \
        python scripts/analytics_report.py --days 30

The same numbers are at GET /api/v1/admin/analytics for emails listed in
ADMIN_EMAILS. Demo accounts are always reported apart from real ones, since
they're mostly recruiters clicking around sample data."""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
os.environ.setdefault("JWT_SECRET_KEY", "unused-by-this-script")


def pct(share):
    return "n/a" if share is None else f"{share:.0%}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    from app.database import SessionLocal
    from app.services.analytics import summary

    db = SessionLocal()
    try:
        s = summary(db, args.days)
    finally:
        db.close()

    print(f"# Wallit usage, last {s['window_days']} days")
    print(f"\n{s['from'][:10]} to {s['to'][:10]}. Tracking started {(s['tracking_since'] or 'never')[:10]}.\n")
    real, demo = s["real_accounts"], s["demo_accounts"]
    rows = [
        ("Active users", real["active_users"], demo["active_users"]),
        ("Came back on another day", real["returning_users"], demo["returning_users"]),
        ("Median session (minutes)", real["median_session_minutes"], demo["median_session_minutes"]),
        ("Assistant messages", real["chat_messages"], demo["chat_messages"]),
        ("Median messages per user who chatted", real["median_chat_messages_per_chatting_user"],
         demo["median_chat_messages_per_chatting_user"]),
        ("Sign-ups / demo sessions started", real["signups"], demo["demo_sessions_started"]),
    ]
    print("| | Real accounts | Demo accounts |\n|---|---|---|")
    for label, r, d in rows:
        print(f"| {label} | {r if r is not None else 'n/a'} | {d if d is not None else 'n/a'} |")

    print("\n## Feature adoption (share of active users who used it)\n")
    print("| Feature | Real accounts | Demo accounts |\n|---|---|---|")
    for label, r in real["feature_adoption"].items():
        d = demo["feature_adoption"][label]
        print(f"| {label} | {r['users']} ({pct(r['share'])}) | {d['users']} ({pct(d['share'])}) |")

    f = s["funnel"]
    print("\n## Landing page\n")
    print(f"- {f['landing_page_visitors']} browsers opened the landing page")
    print(f"- {f['of_those_tried_demo']} of them went on to use the demo")
    print(f"- {f['of_those_signed_in_to_a_real_account']} of them signed in to a real account")
    print("\nBrowsers, not people: one person on a phone and a laptop counts twice.")


if __name__ == "__main__":
    main()
