# Wallit

A personal finance app that connects to your real bank through Plaid, figures out where your
money is going, and lets you ask it questions in plain English.

Next.js · FastAPI · PostgreSQL · Plaid · Claude API · Docker

**[Try the live demo — no account needed](https://wallit-xi.vercel.app/demo)** · **[Live app](https://wallit-xi.vercel.app)** · **[Deployment notes](DEPLOYMENT.md)** · **[Claims and proof](docs/CLAIMS.md)**


<img width="1437" height="892" alt="image" src="https://github.com/user-attachments/assets/9e479ced-13d2-4705-ab34-40fd108d48e2" />

<img width="1444" height="805" alt="{494AC24D-E20F-4AC4-B330-96F23B44B2AA}" src="https://github.com/user-attachments/assets/df2f43d7-5c38-46d5-b5b2-8841aa5edf7c" />

<img width="1236" height="926" alt="{2A516302-B1FC-469E-8304-FE4C65AF03E4}" src="https://github.com/user-attachments/assets/abf13ed8-16f9-4b84-b79c-e21a891f5ec3" />


---

## The problem

Every budgeting app I tried had the same failure mode. They'd import my transactions, file
half of them under "General Merchandise," count a transfer between my own accounts as both
income and spending, and then confidently tell me I'd spent $4,000 that month. The number was
wrong, so I stopped opening the app.

Wallit is my attempt at fixing the part those apps get wrong: getting the data right first,
then making it answerable. You connect a bank, and it categorizes every transaction, finds
your recurring charges, flags spending that's out of line with your own history, and gives
you a chatbot that answers from your actual numbers instead of guessing.

## What it does

**Dashboard** — spend by category, income vs. expenses over the last 7 months, budget
progress with auto-suggested limits, upcoming bills, flagged anomalies, savings goals, and a
what-if slider that projects your balance if you cut a category by some percentage.

**Calendar** — every projected subscription and bill charge laid out by month, navigable
forward and back.

**Subscriptions** — everything detected as recurring, with the billing interval, next
estimated charge, and an AI-suggested cheaper alternative. You can tell it when it's wrong.

**Assistant** — a chatbot with 14 tools wired into your real data. "How much did I spend on
golf this year," "what's due in December," "can I afford a $900 flight," "find cheaper tacos
near Capitol Hill." It can also change things: adjust a budget, create a savings goal,
recategorize a merchant, or dismiss a bad subscription detection.

**Auth** — email/password or Google OAuth, JWT in an httpOnly cookie.

**Demo mode** — `/demo` signs a visitor into a private sandbox with eight months of generated bank
history (paychecks, rent, subscriptions, a Netflix price hike, a couple of splurges). The data is
fake but nothing downstream is: it goes through the same categorization and detection code as a real
Plaid sync, so every chart and flag is computed, not hard-coded. Demo accounts can't connect a bank,
get a capped number of assistant messages, and are deleted after 24 hours.

## Running it

Docker Compose brings up all four services (Next.js, FastAPI, Postgres, Redis):

```bash
git clone https://github.com/rthawani1209/Wallit.git
cd Wallit
cp .env.example .env
docker compose up --build
```

Frontend at `localhost:3000`, API docs at `localhost:8000/docs`.

Before it does anything useful you need to fill in `.env`. The file has generator commands
inline for the two secrets:

| Variable | Where it comes from |
|---|---|
| `JWT_SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `ENCRYPTION_KEY` | `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `PLAID_CLIENT_ID` / `PLAID_SECRET` | free sandbox keys at [dashboard.plaid.com](https://dashboard.plaid.com) |
| `ANTHROPIC_API_KEY` | powers the assistant and the categorization fallback |
| `GOOGLE_PLACES_API_KEY` | optional, only the "cheaper places nearby" tool |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | optional, only Google sign-in |

Plaid sandbox takes `user_good` / `pass_good` at any test bank and hands you a few months of
fake transactions, which is enough to see everything work.

Migrations run automatically when the backend container starts, so there's no separate step
to forget.

## Architecture

```
Next.js (Vercel)  ──/api/* proxy──▶  FastAPI (Railway)  ──▶  Postgres
                                            │
                                            ├──▶ Plaid          bank data
                                            ├──▶ Claude API     categorization, chat, suggestions
                                            └──▶ Google Places  nearby search
                                            
                                     APScheduler re-runs detection nightly
```

```
backend/             FastAPI API
├── app/routers/     HTTP layer, thin
├── app/services/    the actual logic — plaid, categorization, detection, chat, budgets, plans, demo
├── app/models/      SQLAlchemy
├── alembic/         13 migrations
└── tests/           pytest, runs against a real Postgres
frontend/src/        Next.js app
├── app/             routes (dashboard, calendar, subscriptions, assistant, demo, auth)
├── components/      dashboard cards, calendar grid, chat, demo banner, ui primitives
└── lib/             typed API client
scripts/check.sh     runs everything CI runs; use it before pushing
docs/CLAIMS.md       every claim with its proof and a command to reproduce it
```

Routers stay thin on purpose. Everything real lives in `services/`, which is what let the
chatbot reuse `budgets.upsert_budget` and `plans.create_plan` directly instead of
reimplementing them behind the tool interface.

## Decisions worth explaining

This is the part I'd actually want to talk through in an interview.

**Bank tokens are encrypted at rest.** A Plaid access token is a live key to someone's bank
data. It's Fernet-encrypted before it touches the database and the column carries a
`never log this field` comment. The JWT lives in an httpOnly cookie rather than
localStorage, so a script injection can't read it.

**Categorization is a fallback chain, not one method.** Plaid's own category first, then
keyword matching on the merchant name, then a Claude Haiku call, then a guaranteed
catch-all. Nothing ever lands uncategorized. The Claude step returns `None` on any failure
(no key, network error, or a reply that isn't exactly one of my 13 category names) instead of
raising, so a flaky API call degrades to the catch-all rather than breaking a sync.

**Transfers aren't spending.** Moving $2,000 from checking to savings was showing up as both
income and an expense and wrecking every total. They now get their own `Transfer` category
that's excluded from spend, income, and anomaly math. Plaid's `TRANSFER_OUT_SAVINGS` detail
value is specific enough to reclassify as real savings, so that case is handled separately.

**A user's manual category sticks.** `category_is_manual` gets set when someone recategorizes
a transaction by hand, and the sync path checks it before writing. Otherwise the next bank
sync silently reverts the correction, which is the kind of bug that makes people quit an app.

**Subscription detection needed a false-positive fix.** The first version flagged anything
recurring at a consistent amount, which meant weekly grocery runs became "subscriptions" and
a $10 fluctuation in a utility bill became a "price increase." It now requires a stable
3+ charge baseline within ±15% before it'll call the newest charge a price hike, and a
`dismissed_by_user` flag means "this isn't a subscription" is permanent — detection skips
that merchant on every future run instead of re-adding it.

**Anomaly detection is mean + 2σ with a floor.** Over 180 days of history, minimum 4 samples.
A merchant with enough history is judged against itself first, because a $120 grocery run is
normal for Trader Joe's even when most Food charges are $5 coffees; merchants without history fall
back to their category. The extra condition is a $20 absolute gap, because two standard deviations
above a $3 average coffee is $8, and nobody needs an alert about that. Each flag carries a
readable reason like `62% higher than your typical Food spend (avg $41.20)`.

**The chatbot cannot write without confirming.** Six of the 14 tools mutate data. The system
prompt requires the model to describe exactly what it's about to change and wait for the
user's next message before calling the tool, explicitly overriding "just do it, don't ask."
That rule exists because `recategorize_transactions` matches on a substring, and "uber" also
matches "Uber Eats" — one confident tool call could recategorize months of food spending as
transportation.

**Tools return totals, not just rows.** `get_transactions` caps its returned list but computes
`count` and `total_amount` over the full match set, with a note telling the model to use those
figures rather than adding up the visible rows. Language models will happily sum a truncated
list and present the result as your annual total.

**Prompt caching on the system prompt and tool schemas.** They're byte-identical on every
request and the tool definitions are long, so a cache breakpoint on the last one cuts the
cost of a multi-turn conversation substantially.

**The mobile Safari cookie bug.** This one took the longest. In production the frontend is on
Vercel and the API is on Railway — two different domains, so the login cookie is cross-site,
and mobile Safari drops those silently. Login worked on my laptop and failed on my phone with
no error anywhere. The fix is in `next.config.ts`: a rewrite proxies `/api/*` through Vercel's
own domain to Railway, which makes the cookie same-site again. The catch is that setting
`NEXT_PUBLIC_API_URL` in production undoes it, because then the browser calls Railway
directly again. That's documented in `DEPLOYMENT.md` so future me doesn't reintroduce it.

Google's OAuth `state` has the same problem — it has to survive a redirect out to Google, back
again, and through the proxy — so it's a short-lived signed JWT verified on its own signature
instead of a cookie.

**CI gates the deploy.** Both hosts auto-deploy from `main`, so
[the workflow](.github/workflows/ci.yml) has to catch things first: typecheck and build the
frontend, import the backend app (catches syntax errors, bad imports, broken config), and run
every migration against a fresh Postgres. A broken migration chain fails the build instead of
the production database.

## API

All routes are under `/api/v1` and authenticate via the session cookie. Full interactive docs
at `/docs` when the backend is running.

| | |
|---|---|
| `auth` | `signup`, `login`, `logout`, `me`, `google/start`, `google/callback` |
| `plaid` | `link-token`, `exchange-token`, `resync` |
| `transactions` | list, `PATCH` category, `summary`, `cashflow`, `upcoming-bills`, `anomalies` |
| `subscriptions` | list, `calendar` |
| `budgets` | `progress`, `PUT /{category_id}` |
| `plans` | list, create, patch |
| `chat` | post a conversation, get a reply |
| `simulate` | what-if projection |
| `accounts`, `categories` | list |

## What's not done

- **One bank per user.** Linking a second bank replaces the first one's access token. A
  `plaid_items` table with a cursor per bank is next.
- **Still on Plaid sandbox.** Going to production is mostly swapping keys, plus registering
  the OAuth redirect URI for banks like Chase that use it. `DEPLOYMENT.md` covers it.
- **Savings goal progress is pledged, not verified.** It tracks contribution × months elapsed
  rather than reconciling against actual transfers.
- **Detection runs nightly on a single process.** Fine at this size. Real multi-user load
  wants a proper task queue, which is what Redis is sitting there for.
- **`frontend/README.md` is still create-next-app boilerplate.**

## Notes

Built solo over about a month, 113 commits. `DEPLOYMENT.md` has the full Vercel + Railway
walkthrough including the env var gotchas.
