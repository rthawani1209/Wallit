# Project design document — Wallit (Personal Finance & Budget Planning App)

**Owner:** Rohan Thawani
**Project name:** Wallit
**Purpose of this document:** This is a complete project brief for Claude Code (or any collaborator) to read before writing any code. It covers the full functionality of the app in plain terms first, then the technical implementation. Read this whole document before starting work.

---

## 0. How to work with me on this project

Read this section first — it governs *how* you help, not just *what* to build.

- **Priority order, explicitly:** this is a real, interactive, user-facing web application first. Docker, CI/CD, and cloud deployment are tools in service of shipping that app — not the project itself. Do not let infrastructure work crowd out building actual features the user can see and use. If a phase is dragging into pure DevOps/config work with nothing new visible in the app, flag it to me.
- **This is not just a finance tracker or an ETL pipeline with a UI on top.** The core identity of this app is a budget-aware planning and discovery tool — it should help the user actually *do* things with their money (plan a trip, find something they can afford nearby, see what's coming up, find a cheaper alternative), not just report numbers back at them. Every feature should pass this test: does it help the user decide or do something, or does it just display data? Prefer the former.
- **I am learning as we build.** Do not just generate finished code silently. As you implement each piece, briefly explain *what* you're doing and *why* — especially for concepts I'm new to (WebSockets, Redis, Docker, CI/CD, ETL jobs, Plaid's auth flow, places/location APIs). Treat this like pair programming with a teacher, not a code-generation service.
- **Prefer small, reviewable steps over huge diffs.** Build incrementally — one feature/service at a time, in the phase order laid out in Section 8 — rather than scaffolding the entire app in one shot.
- **Ask before assuming on ambiguous decisions**, but don't ask about things this document already answers.
- **This document is the source of truth.** If something in this doc conflicts with a default you'd normally reach for, follow this doc and flag the conflict to me rather than silently picking your own default.
- **Do not build the AI bot feature yet.** It's listed in Section 8.12 as a future phase — we'll design it together later once the core app is working. Don't scaffold it preemptively.
- **Before starting Phase 1, check my VS Code extensions and install anything missing.** Run `code --list-extensions` to see what I already have, then install whatever's missing from this list (via `code --install-extension <id>`), explaining briefly what each one does as you install it:
  - `ms-python.python` + `ms-python.vscode-pylance` — Python language support/autocomplete for the FastAPI backend
  - `ms-azuretools.vscode-docker` — Docker file support and a UI for managing containers/images
  - `dbaeumer.vscode-eslint` — JavaScript/TypeScript linting for the Next.js frontend
  - `esbenp.prettier-vscode` — auto code formatting (JS/TS/CSS)
  - `bradlc.vscode-tailwindcss` — Tailwind CSS autocomplete, if we end up using Tailwind for styling
  - `eamodio.gitlens` — richer Git history/blame info inline, useful since this is going on GitHub
  - `ckolkman.vscode-postgres` or `mtxr.sqltools` (+ Postgres driver) — lets me browse/query the Postgres database directly from VS Code instead of only through the terminal
  - `humao.rest-client` or Thunder Client (`rangav.vscode-thunder-client`) — lets us manually test backend API endpoints from inside VS Code as we build them
  - `github.vscode-github-actions` — inline status/support for the GitHub Actions CI/CD workflows we'll be writing in Phase 6

---

## 1. What this app is, in plain terms

Think of it less as "a budget tracker" and more as **a planning assistant that happens to know your real spending.** Most student finance-tracker projects stop at "here are your transactions in a chart." This app goes further: it uses your real (sandboxed) bank data to help you actually plan and decide things — plan a trip within budget, find things nearby you can actually afford, see upcoming bills before they surprise you, and get nudged toward cheaper alternatives when you're overpaying for something.

**Primary goals, in order:**
1. Build a genuinely working, genuinely useful full-stack app — not a data-display shell.
2. Deploy it live using Docker + CI/CD + a cloud host, so it's a real, running product.
3. Use it as a portfolio/resume piece demonstrating skills current internship applications screen for: testing, containerization, CI/CD, cloud deployment, multiple real API integrations, and an LLM feature.
4. Use it as a learning vehicle — I want to understand each piece as we build it.

---

## 2. Full application functionality (in depth, non-technical)

This section describes exactly what a user can do in the app, feature by feature, in plain language. This is the actual product spec — read this before touching the technical sections.

### 2.1 Core: Real user accounts (sign up, log in, your own private data)
This is a real multi-user website, not a single-user demo. Anyone can create an account with an email and password (or "sign in with Google"), log in securely, and have their own completely private space in the app — their own connected accounts, plans, goals, and settings, invisible to every other user. This is standard account/auth functionality, independent of anything Plaid-related — it's what makes this "a website people can actually use," as opposed to a local script only one person runs. See Section 5.1 for the technical implementation.

### 2.2 Core: Connected accounts & spending overview
Once logged in, the user connects a bank account through Plaid's standard bank-linking flow — the same kind of "click your bank, log in, done" experience real fintech apps use. Once connected, the app pulls in real transaction history and account balances. The home dashboard shows: current balance across accounts, this month's spending so far, a breakdown of spending by category, and a scrollable list of recent transactions. This is the foundation everything else is built on top of.

**Important distinction:** account creation/login (2.1) is unlimited and works for anyone, always. Bank-linking (this section) depends on which Plaid environment the deployment is configured for — Sandbox (unlimited fake test banks, always available to anyone) or the free Trial plan (up to 10 real bank connections). A user can always sign up and use the app even in Sandbox mode; only the "is this a real bank or a fake one" part is capped.

### 2.3 Feature: "What-if" budget simulator
Right on the dashboard, the user can drag a slider like "cut dining out by 20%" and watch their projected end-of-month balance update live, without reloading the page. This makes the app feel responsive and useful from day one rather than just being a static report.

### 2.4 Feature: Automatic categorization, subscriptions & anomalies
Behind the scenes, a nightly job looks at new transactions and automatically sorts them into categories (no manual tagging required after the first pass), flags recurring charges as subscriptions, and flags any transaction that looks unusually large for its category. The user doesn't do anything to trigger this — it just happens, and results show up the next time they open the app.

### 2.5 Feature: Cheaper-alternative finder *(idea 4)*
When the app detects a recurring subscription (say, a $15/month streaming service or a $60/month gym membership), it surfaces a simple suggestion: "you're paying $X for [service] — here's a cheaper or free alternative" where reasonable. This doesn't need to be exhaustive or perfect — even a small curated mapping of common subscription categories to known cheaper alternatives is a meaningful, demoable feature. The point is the app doesn't just tell you what you're spending, it nudges you toward a better decision.

### 2.6 Feature: Bill & obligation calendar *(idea 3)*
A calendar view showing upcoming bills and subscription charges by due date — built from the subscription detection in 2.3. Instead of only looking backward ("here's what you spent"), the app looks forward: "here's what's coming up in the next two weeks and roughly how much you'll owe." This turns the subscription data from something passive into something actionable — the user can see a real payment calendar, not just a list.

### 2.7 Feature: Budget-aware trip/event planner *(idea 1)*
This is the app's signature feature — the thing that makes it feel like a planning tool, not a tracker. The user creates a "plan" — a trip, an event, a big purchase — and sets a target budget (e.g., "$800 for a weekend trip to Portland" or "$300 for a birthday party"). The app then:
- Breaks the budget down into a simple line-item estimate (e.g., lodging, food, activities, transport) that the user can adjust.
- Tracks actual spending against the plan as the user makes real purchases tagged to that plan (or estimates it from category-matched transactions).
- Shows a clear "on track / over budget / under budget" status as the date approaches.
This turns a savings goal from an abstract number into something concrete the user is actually working toward.

### 2.8 Feature: Real-world budget-based discovery *(idea 2)*
This is what makes the planner genuinely different from a spreadsheet: inside a plan (or from the main dashboard), the user can search for real things near them that fit what's left of their budget — "dinner spots near me under $30," "things to do in Portland under $50," "cheaper gym alternatives near me." This is powered by a real places/location API (see Section 5) pulling in actual nearby businesses, ratings, and price level — not a static hardcoded list. The budget context is what makes it more than a generic maps search: results are filtered against what the user has actually got left to spend.

### 2.9 Feature: Savings goal → real plan *(idea 5)*
Goals aren't just a number with a progress bar — a goal *is* a plan (see 2.6). If the user sets a goal like "save for a trip to Japan," that goal becomes a plan with a real destination, a real estimated cost (pulled the same way as 2.6/2.7), and the app shows how their actual current savings rate maps onto realistically affording it — "at your current pace, you'll hit this goal by [date]" — recalculated automatically as new transactions come in, not a number the user has to manually update.

### 2.10 Feature: Natural-language query bar
A search/query bar where the user can type plain questions like "how much did I spend on food last month" or "am I on track for my Japan trip" and get a real, accurate, plain-English answer — powered by the Claude API translating the question into a real query against the user's actual data (not a generic chatbot giving vague answers).

### 2.11 Feature (future, not yet designed): AI bot
Deferred — see Section 8.12. Not part of the v1 functionality list above; will be scoped in a future session.

### 2.12 What this app is *not*
To keep scope sane: this is not a bill-pay app (no money actually moves), not a budgeting app that requires manual entry (everything is pulled from real — sandboxed — transaction data), and not a social app (no feeds, no sharing with other users in v1, though group planning could be a future extension).

---

## 3. Tech stack (final decisions — do not substitute without discussing)

| Layer | Choice | Notes |
|---|---|---|
| Frontend | **Next.js** (React, App Router) | TypeScript preferred over plain JS |
| Authentication | **JWT-based sessions** (bcrypt password hashing, e.g. `passlib` + `python-jose`, or `fastapi-users` library) | Real signup/login for real multi-user accounts — see Section 5.1. Independent of Plaid; every user can sign up and log in regardless of which Plaid environment is active. |
| Backend | **FastAPI** (Python) | |
| Database | **PostgreSQL** | Primary data store |
| Caching / fast reads | **Redis** | For cached balances, rate limiting if needed |
| Bank data | **Plaid API — Sandbox mode** | Fake banks, fake data, real integration pattern. Never use real bank credentials. |
| Places / location data | **Google Places API** (or equivalent — decide when we reach Section 8.9) | Powers the real-world discovery feature (Section 2.8). This is a second genuine external API integration, distinct from Plaid. |
| AI features | **Claude API (Anthropic)** | Used for the natural-language query feature (Section 2.10). NOT for the "AI bot" — that's a separate future feature, see Section 2.11 / 8.12. |
| Containerization | **Docker** | Separate containers for frontend, backend, and (if used) worker/scheduler |
| CI/CD | **GitHub Actions** | Lint + test on every push; auto-deploy on merge to `main` |
| Deployment target | **Render** (decided — Fly.io no longer has a free tier for new users as of 2026) | Two Render services from the same codebase: one real (Trial-plan Plaid keys, my own real data + ~8 users), one sandbox (fake data, for anyone to try risk-free) — see Section 8.7. Full AWS/Kubernetes is a stretch goal, not a requirement — see Section 9 |
| Testing | **pytest** (backend), basic component tests for frontend if time allows | Real test suite is a resume requirement, not optional |
| Scheduled jobs | Simple cron-based job or APScheduler inside the backend container | Used for nightly transaction categorization, subscription/anomaly detection, and goal-forecast recalculation |

**Explicitly out of scope for v1:** Kubernetes (stretch goal only, see Section 9), microservices split, mobile app, real (non-sandbox) bank connections, payment processing, real money movement of any kind, social/multi-user features.

---

## 4. Architecture overview

```
User (browser)
     |
     v
Frontend (Next.js) --------> Backend (FastAPI)
                                   |
                    -------------------------------------------------
                    |                |                |             |
                    v                v                v             v
              PostgreSQL          Redis          Plaid API      Places API
           (transactions,      (cached reads,     (sandbox      (real-world
            users, plans,       rate limiting)     bank data)    discovery)
            categories,
            bills)
                    ^
                    |
          Nightly scheduled job
          (categorizes transactions,
           detects subscriptions/anomalies,
           recalculates goal forecasts,
           refreshes bill calendar)
```

- The frontend never talks to Plaid, Places, or Postgres directly — everything goes through the FastAPI backend. This keeps API keys and DB credentials server-side only.
- The scheduled job is the ETL layer: it turns raw Plaid transaction dumps into categorized, analyzable data, and keeps the bill calendar and goal forecasts fresh without the user doing anything manually.

---

## 5. Data model (initial schema)

Starting point — refine as needed, but don't wildly diverge without explaining why.

### 5.1 Authentication approach
Real multi-user auth, not a single hardcoded user. Recommended approach for this stack:
- **Password auth:** user signs up with email + password. Password is hashed with bcrypt (never stored in plain text, never logged).
- **Sessions:** on login, issue a JWT (JSON Web Token) — a signed token the frontend stores and sends with each request to prove who's logged in, so the user isn't re-entering their password on every page.
- **Multi-provider auth, built in from Phase 1 (decided during Phase 1 implementation):** email/password AND "Sign in with Google"/"Sign in with Apple" are all first-class from the start, not deferred. `User.password_hash` is nullable (OAuth-only users have none). A separate `linked_identities` table holds one row per external provider linked to a user (`provider` + `provider_user_id`, unique together), so a single user can link multiple providers over time.
- **Every backend query is scoped to the logged-in user's `user_id`.** This is the actual security boundary that keeps User A from ever seeing User B's data — enforce it consistently, not just on some endpoints.
- **Frontend route protection:** pages like the dashboard, plans, and settings should redirect to login if there's no valid session — same "protected route" pattern already planned for other parts of the app.
- This is genuinely standard, well-documented territory (FastAPI has established patterns for JWT auth, e.g. via `fastapi-users` or a hand-rolled implementation with `passlib` + `python-jose`) — Claude Code should walk through the choice of library vs. hand-rolled when we get to Phase 1.

```
users
  id (uuid, PK)
  email (unique)
  password_hash (bcrypt — never store plain text; nullable, OAuth-only users have none)
  created_at
  plaid_access_token (encrypted at rest — never log this; nullable until they connect a bank)

linked_identities
  id (uuid, PK)
  user_id (FK -> users.id)
  provider ('google', 'apple', etc.)
  provider_user_id (the provider's unique ID for this user)
  created_at
  unique(provider, provider_user_id)

accounts
  id (uuid, PK)
  user_id (FK -> users.id)
  plaid_account_id
  name
  type
  current_balance

transactions
  id (uuid, PK)
  account_id (FK -> accounts.id)
  plaid_transaction_id
  amount
  merchant_name
  date
  category_id (FK -> categories.id, nullable until categorized)
  plan_id (FK -> plans.id, nullable — set if this transaction is tagged to a specific plan/goal)
  is_subscription (bool, default false)
  is_anomaly (bool, default false)

categories
  id (uuid, PK)
  name

plans
  id (uuid, PK)
  user_id (FK -> users.id)
  type              -- 'trip', 'event', 'purchase', 'savings_goal'
  name              -- e.g. "Trip to Japan", "Sarah's birthday party"
  target_amount
  target_date (nullable)
  location (nullable -- used for discovery/planner features, e.g. "Portland, OR")
  created_at

plan_line_items
  id (uuid, PK)
  plan_id (FK -> plans.id)
  label             -- e.g. "Lodging", "Food", "Activities"
  estimated_amount
  actual_amount (nullable, rolls up from tagged transactions)

subscriptions
  id (uuid, PK)
  user_id (FK -> users.id)
  transaction_pattern_id -- links to the recurring transaction group it was detected from
  merchant_name
  amount
  billing_interval  -- e.g. 'monthly'
  next_estimated_date
  cheaper_alternative (nullable, text suggestion)

bills
  id (uuid, PK)
  user_id (FK -> users.id)
  source_subscription_id (FK -> subscriptions.id, nullable)
  name
  amount
  due_date
```

**Indexing notes (this matters for your resume bullets — do this properly):**
- Index `transactions.account_id`, `transactions.date`, `transactions.category_id`, and `transactions.plan_id`.
- Composite index on `(account_id, date)` for the "recent transactions" query pattern.
- Index `bills.due_date` for the calendar view query.

---

## 6. Backend API surface (initial)

REST endpoints under `/api/v1/`:

```
POST   /api/v1/plaid/link-token          -- create a Plaid Link token for the frontend to open the bank-connect flow
POST   /api/v1/plaid/exchange-token      -- exchange a public token for an access token, store it
GET    /api/v1/accounts                  -- list connected accounts + balances
GET    /api/v1/transactions              -- list transactions, filterable by date range / category / plan
GET    /api/v1/transactions/summary      -- aggregated spend by category for a given period
GET    /api/v1/simulate                  -- what-if simulator: takes hypothetical % changes, returns projected balance
GET    /api/v1/subscriptions             -- detected recurring subscriptions, with alternative suggestions
GET    /api/v1/anomalies                 -- flagged unusual transactions
GET    /api/v1/bills                     -- upcoming bills, calendar-view friendly (date range filterable)
POST   /api/v1/plans                     -- create a plan (trip/event/purchase/goal)
GET    /api/v1/plans                     -- list plans with progress/status
GET    /api/v1/plans/{id}                -- single plan detail incl. line items and tagged transactions
POST   /api/v1/plans/{id}/line-items     -- add/edit a line item on a plan
GET    /api/v1/discover                  -- real-world discovery: takes a query + plan_id (for budget context) + location, returns nearby options
POST   /api/v1/query                     -- natural-language query endpoint (Claude API)
```

---

## 7. UX notes / what the interface should feel like

- Home dashboard: balance, this month's spend, category breakdown, what-if slider, and a short "upcoming bills" preview — this is the "here's my life at a glance" screen.
- Plans section: a list of active plans (trips/events/goals) each showing budget vs. actual and a status (on track / over / under). Clicking into one shows line items and the discovery search (Section 2.8) scoped to that plan's remaining budget.
- Bills/calendar view: a simple calendar or upcoming-list showing what's due and when.
- Subscriptions view: list of detected recurring charges, each with a "cheaper alternative" suggestion where available.
- Query bar: accessible from the dashboard, not buried in a settings menu — this should feel like a core feature, not an easter egg.
- Full visual polish (motion, glassmorphism, etc.) comes later — see Section 8.13 — but the *layout and flow* described here should be right from early on, since restructuring UX late is more painful than restyling it.

---

## 8. Feature build phases

Build in this order. Each phase should be a working, demoable state before moving to the next.

### 8.1 — Phase 1: Core plumbing + real authentication
- Docker Compose setup for local dev: frontend, backend, Postgres, Redis all running together with one command.
- FastAPI skeleton with health-check endpoint.
- Next.js skeleton with a placeholder dashboard page.
- Postgres schema migrations (Alembic).
- **Real signup/login** (Section 5.1): email + password auth, hashed passwords, JWT sessions, protected routes on the frontend. Build and test this before anything else — every other feature depends on knowing which user is asking.
- Plaid sandbox integration end to end: Link token → public token exchange → pull real sandbox transactions → store in Postgres, scoped to the logged-in user.
- **Done when:** I can sign up for a real account, log in, log out, get redirected to login if I try to access the dashboard while logged out, and — once logged in — connect a fake bank via Plaid's sandbox flow and see real (fake) transactions tied to my account in the database.

### 8.2 — Phase 2: Dashboard basics + what-if simulator
- Transaction list view, balance summary card, manual category assignment (before automating it), spend-by-category chart.
- The what-if simulator (Section 2.3) — live-recalculating slider.
- **Done when:** dashboard shows real data with basic charts, and at least one thing responds live to user input.

### 8.3 — Phase 3: Automation (categorization, subscriptions, anomalies)
- Nightly job: rule-based auto-categorization, subscription detection (recurring merchant/amount/interval), anomaly detection (rolling average + standard deviation).
- **Done when:** transactions get auto-categorized overnight, and subscriptions/anomalies views populate automatically.

### 8.4 — Phase 4: Cheaper-alternative finder
- Small curated mapping (category/merchant → suggested cheaper alternative) surfaced on the subscriptions view.
- **Done when:** at least a handful of common subscription types show a real alternative suggestion.

### 8.5 — Phase 5: Bill & obligation calendar
- Build the `bills` table from detected subscriptions, expose the calendar-friendly endpoint, build the calendar/upcoming view on the frontend.
- **Done when:** the user can see upcoming charges by date without manually entering anything.

### 8.6 — Phase 6: Testing + CI/CD
- pytest suite covering categorization, subscription detection, anomaly detection, and core API endpoints so far.
- GitHub Actions: lint + test on every push, build + deploy on merge to `main`.
- **Done when:** green checkmark on every push, merging to `main` auto-deploys.

### 8.7 — Phase 7: Deploy live
Two deployments of the exact same codebase — not two separate apps, and not something to describe differently on a resume. Both are "the app I built." The only difference is which Plaid data source each one is configured to use.

- **`finance-app` (real):** Render service running Plaid's Trial plan (real bank data). This is what I actually use day to day with my own real account, plus up to ~8 real friends/family. Its own Postgres database.
- **`finance-app-try-it` (sandbox):** A second Render service, same repo, same Dockerfile, configured with Sandbox Plaid keys instead. This is the link that goes in the README/resume for anyone who wants to click around without connecting a real bank — same features, same UI, fake test data instead of real data. Its own separate Postgres database.
- Setup cost is small: same repo, two Render services (or two blocks in one `render.yaml`), two sets of environment variables. Not a parallel codebase to maintain.
- **Resume framing:** describe this as one project — "I built a full-stack budget planning app" — not as "I built a demo." The sandbox link exists purely so a stranger can try it risk-free; it doesn't change what the project *is*. If the README needs to explain the two links, phrase it practically: "Try it live (sandbox test data, no real bank needed)" vs. "This is also running in production with real Plaid data for my own use" — informational, not a caveat on the project's legitimacy.
- Public GitHub repo with a README that includes a short demo video or screenshots of the app working with real data, alongside the sandbox link, so anyone evaluating the project sees it genuinely works without needing to trust it with their own bank info.
- **Done when:** both services are live, I've connected my own real bank on the real deployment and it works end to end, and the sandbox deployment lets anyone click "connect bank" and use Plaid's fake test bank with zero setup.

### 8.8 — Phase 8: Budget-aware planner (trips/events/purchases)
- `plans` and `plan_line_items` tables, plan CRUD endpoints, plan detail UI with line items and budget-vs-actual tracking, transaction tagging to a plan.
- **Done when:** I can create a plan with a budget, break it into line items, tag real transactions to it, and see accurate progress.

### 8.9 — Phase 9: Real-world discovery
- Integrate the Places API, build the `/discover` endpoint (query + location + remaining plan budget → filtered real results), build the discovery search UI inside a plan.
- **Done when:** inside a plan, I can search "dinner near me under $30" and get real nearby results filtered by what's left in the budget.

### 8.10 — Phase 10: Savings goal → plan integration
- Wire `type: 'savings_goal'` plans into the same discovery/estimate flow as trips, add the "at your current pace, you'll hit this by [date]" forecast calculation.
- **Done when:** a savings goal behaves like a real plan with a live-updating forecast, not just a static progress bar.

### 8.11 — Phase 11: Natural-language query bar
- `/query` endpoint using the Claude API to translate a plain-English question into a structured, validated filter/aggregation against the user's real data (not raw SQL generation from user input).
- **Done when:** I can type a few different natural questions and get accurate answers back.

### 8.12 — Phase 12: AI bot (future — do not build yet)
- Placeholder only. Design together in a future session once everything above is stable. Do not scaffold, stub, or guess at this feature until told to.

### 8.13 — Phase 13 (stretch, time-permitting): Visual polish pass
- Only after Phases 1-11 work. Framer Motion for transitions/micro-interactions, glassmorphism cards, a real cash-flow Sankey diagram (D3.js), refined typography and dark mode.
- Do not start this phase until the app functionally works. A working plain app beats a beautiful broken one.

### 8.14 — Phase 14 (stretch, optional): Kubernetes
- Only pursue if there's a genuine multi-service reason to (e.g. splitting the scheduled ETL job into its own service from the API). See Section 9 for the honest reasoning.

---

## 9. Honest notes on Kubernetes

Full Kubernetes is overkill for a solo project with a couple of services. Don't force it in just to list it on a resume — that reads poorly in an interview if I can't explain a real reason I needed it. If we do want to legitimately earn a Kubernetes line, the honest path is: split the scheduled ETL/categorization job into its own separate service from the main API, and orchestrate the resulting 2-3 services locally with `kind` or `minikube`. Optional, and only after Section 8 phases 1-11 are done.

---

## 10. DevOps details

### 10.1 Docker
- Separate `Dockerfile` for frontend and backend.
- `docker-compose.yml` for local dev spinning up frontend, backend, postgres, redis with one command (`docker compose up`).
- Multi-stage builds for the frontend (build stage + slim production stage) to keep image size down.

### 10.2 CI/CD (GitHub Actions)
Minimum pipeline, triggered on every push:
1. Install dependencies (backend + frontend).
2. Run linters (ruff/flake8 for Python, eslint for TS/JS).
3. Run pytest suite.
4. (On merge to `main` only) Build Docker images, push to a registry, trigger deployment on Render/Fly.io.

### 10.3 Secrets management
- Plaid keys, Places API key, database credentials, and the Claude API key must **never** be committed to the repo.
- `.env` files locally (in `.gitignore` from day one); the deployment platform's secret manager in production; GitHub Actions secrets for anything CI needs.

### 10.4 Environments
- Local (Docker Compose) and production (Render/Fly.io). No separate staging environment needed for a solo project.

---

## 11. Testing strategy

- Backend: pytest covering categorization logic, subscription/anomaly detection, plan progress calculation, bill calendar generation, and API endpoint behavior (including error cases — e.g. Plaid or Places API being down).
- Aim for meaningful coverage of business logic, not 100% coverage for its own sake.
- Frontend: basic component tests only if time allows after backend testing is solid; not a priority for v1.

---

## 12. How this maps back to the resume

(Context only — not something to build.)

- Docker + GitHub Actions CI/CD + live cloud deployment → closes the "no DevOps keywords" gap.
- Real Plaid integration + ETL-style categorization job → extends existing SEH data-engineering resume experience into a new context.
- Places API integration for real-world discovery → a second genuine external API integration, shows range beyond "one API demo."
- pytest suite → closes the "no testing" gap.
- Claude API natural-language query feature → real LLM integration, not a chatbot wrapper.
- The planner/discovery/bills features together → move the project's pitch from "I built a finance tracker" (common, forgettable) to "I built a budget-aware planning tool" (distinct, better interview story).
- Public GitHub repo with real commit history → fixes the "empty GitHub" problem flagged as the single biggest resume issue.

---

## 13. Open questions to resolve together before/while building

- Render vs. Fly.io for deployment — decide at Phase 7.
- Exact category list granularity.
- Which places API to use and how to keep it within free-tier limits during development.
- Curated list of "cheaper alternatives" for the subscription finder — build this together as we hit real detected subscriptions.
- AI bot feature (Section 2.11 / 8.12) — fully undesigned, intentionally deferred.

---

*End of design document. Section 2 is the full functionality spec — read it in full before starting any code. Claude Code: start with Phase 1 (Section 8.1) once I confirm I'm ready, and follow the working style described in Section 0 throughout.*
