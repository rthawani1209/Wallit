# Claims and proof

One row for each thing Wallit claims, the proof behind it, and the command that reproduces it. If a claim can't be proven here, it doesn't go on a resume.

Every command runs from `backend/` against a throwaway Postgres (see `scripts/check.sh`), e.g.
`DATABASE_URL=postgresql://ci:ci@localhost:5432/ci python -m pytest -q tests/test_detection.py`.
`scripts/check.sh` runs all of them, the same way CI does.

| Claim | Proof | Reproduce |
|---|---|---|
| Every transaction gets a category: Plaid's category, then merchant keywords, then Claude, then a catch-all | `backend/tests/test_categorization.py` | `pytest tests/test_categorization.py` |
| Transfers between your own accounts are excluded from spending, budgets and the what-if simulator | `test_budgets.py::test_transfers_get_no_budget_row`, `test_detection.py::test_transfers_never_feed_anomaly_stats` | `pytest tests/test_budgets.py tests/test_detection.py -k transfer` |
| Subscription detection requires a steady amount and every gap to fit the cadence, so grocery runs and repeat lunches aren't flagged | `test_detection.py` (monthly charge detected; varying groceries, irregular gaps and two-charge cases rejected) | `pytest tests/test_detection.py -k "subscription or gaps or two_similar"` |
| Price hikes are flagged against the subscription's previous amount | `test_demo.py::test_seed_is_realistic_and_runs_through_real_detection` (Netflix $15.49 → $17.99) | `pytest tests/test_demo.py -k realistic` |
| Unusual-spending alerts use mean + 2σ against the merchant's own history first, then the category's, with a $20 floor | `test_detection.py` (merchant beats category, spike at a known merchant, small-gap coffee not flagged) | `pytest tests/test_detection.py -k "anomaly or merchant"` |
| A user's manual category survives a bank resync | `test_sync.py::test_manual_category_survives_resync` | `pytest tests/test_sync.py -k manual` |
| Plaid sync applies added, modified and removed transactions, so a pending charge that posts isn't counted twice | `test_sync.py` (modified amount, pending removed) | `pytest tests/test_sync.py` |
| Stale rows are pruned only after a complete, full-size sync, so a partial fetch never deletes real history | `test_sync.py` (still loading, short fetch, complete fetch) | `pytest tests/test_sync.py -k prune` |
| Recruiter demo: one click creates a private sandbox with 8 months of generated bank history, analyzed by the real pipeline, and deleted after 24 hours | `test_demo.py` (seed, categorization path, session reuse, cleanup) and the `/demo` page | `pytest tests/test_demo.py`, then open `/demo` |
| The demo can't touch Plaid, caps assistant messages and rate-limits new sessions per IP | `test_demo.py::test_demo_users_cannot_touch_plaid`, `::test_demo_chat_is_capped`, `::test_new_demo_sessions_are_rate_limited_per_ip` | `pytest tests/test_demo.py -k "plaid or capped or rate"` |
| CI blocks deploys: lint, typecheck, build, import check, migrations on a fresh database, and the test suite | `.github/workflows/ci.yml`, `scripts/check.sh` | `scripts/check.sh` |

## Not claimable yet
- Assistant tool use and prompt caching work against the live API, but there's no automated test that calls Claude. An eval with recorded cache-hit numbers is on the plan.
- Performance numbers (sync time, demo creation time) need a committed benchmark results file before they're quoted.
