# Usage analytics

Wallit records what people do in its own Postgres table, `analytics_events`. There's no third-party tracker. The point is to have real, checkable numbers about how the app is used. Every number traces back to rows you can query.

## What's recorded

| Event | Recorded by | When |
|---|---|---|
| `signup`, `login` | backend | after a successful sign-up or login (`method`: password or google) |
| `demo_started` | backend | a new demo account is created |
| `bank_linked`, `resync` | backend | after the sync finishes |
| `chat_message` | backend | a message passes the rate and demo limits (`streamed`: true or false) |
| `forecast_viewed` | backend | the forecast is served |
| `budget_set`, `transaction_recategorized`, `plan_created` | backend | after the change is saved |
| `page_view` | frontend | a page from a fixed list is opened (`/`, `/demo`, `/signup`, `/login`, `/dashboard`, `/calendar`, `/subscriptions`, `/assistant`) |

The backend records what really happened, so a refresh or an ad blocker can't change those counts. Page views come from the browser and are the only events that exist before someone signs in. They carry a random `visitor_id` that the browser keeps in localStorage.

Not recorded:
- emails, names, amounts, merchant names, or message text;
- page views from browsers that send Do Not Track or Global Privacy Control.

Every row is tagged `is_demo`, so recruiters clicking around sample data never get mixed into real-user numbers. `user_id` is not a foreign key, so demo events still count after the nightly cleanup deletes the demo account.

## Getting the numbers

- **In the browser.** Set `ADMIN_EMAILS=you@example.com` on the Railway backend, log in with that email, and open `/api/v1/admin/analytics?days=30`. Anyone else gets a 404.
- **As a Markdown table.** Point `DATABASE_URL` at the production database (Railway shows a public URL under the Postgres service's Connect tab) and run:
  ```bash
  python scripts/analytics_report.py --days 30
  ```
- **Raw SQL, to back up any number:**
  ```sql
  SELECT name, is_demo, count(*), count(DISTINCT user_id)
  FROM analytics_events WHERE created_at > now() - interval '30 days'
  GROUP BY 1, 2 ORDER BY 1, 2;
  ```

The report covers:
- active and returning users;
- median session length (first to last event on a day);
- assistant messages;
- the share of active users who used each feature;
- a landing page → demo → real account funnel.

Real accounts and demo accounts are always reported separately.

## Reading the numbers honestly

- Tracking started when migration `0015` was deployed. Nothing before that date exists, so don't quote numbers from earlier.
- A visitor is a browser, not a person. One person on a phone and a laptop counts as two.
- "Session length" is the time from first to last event on a day. Someone who opens one page and leaves counts as 0 minutes.
- Small numbers are fine to quote as counts ("12 people tried the demo in its first week"). Avoid percentages on fewer than about 20 users.
- `summary()` loads the window's events into memory. That's fine for thousands of rows. It would need SQL aggregation at a much larger scale.
