# Before and after

Every number here comes from `scripts/benchmarks/run.sh`. Both versions are measured the same way, on the same machine, against the same simulated bank.

- **Before:** `70050e4`, the last commit before the work that started on Oct 27, 2026.
- **After:** `781ab26`, the head of PR #3. Current `main` (`e06a102`) gives the same numbers, because PR #3 doesn't touch sync or login.

Measured on Nov 5, 2026 in a Linux container with Postgres 16 and Python 3.12. Running the script again gives the same counts. Times move by a few hundredths of a second.

## Results

| What | Before | After |
|---|---|---|
| Resync time, one day after linking | 10.38 s | 0.04 s |
| Plaid pages requested per resync | 17 | 1 |
| Transactions reprocessed per resync | 1,141 | 22 |
| SQL statements per resync | 1,156 | 32 |
| Linking a bank (first sync) | 10.56 s | 0.50 s |
| Spending stored vs what the bank holds | $455.46 too high | exact |
| Rows the bank had already removed, still stored | 8 | 0 |
| 25 wrong passwords in a row | all 25 allowed | 15 blocked after 10 |
| Login response, unknown vs real email | 3 ms vs 221 ms | 222 ms vs 222 ms |
| Backend tests | 0 | 64 |
| Frontend lint errors | 11 | 0 |
| Steps for a recruiter to see the app with data | sign up (5 fields) and link a bank | open `/demo` |

## Where each change comes from

- **Resync and linking time.**
  - Before, every sync started from an empty cursor and then always waited 5 × 2 seconds for more data, even when Plaid had already said the history was complete.
  - Now each bank keeps Plaid's cursor (`90c3eed`), so a resync asks only for what changed. The wait on the first sync stops as soon as Plaid says the history is complete.
  - With real Plaid, every page is also a network round trip, so the gap between 17 pages and 1 page is larger in production than shown here.
- **Spending accuracy.**
  - Before, sync read only Plaid's `added` list. A pending card charge that later posted under a new id was stored twice, and a merchant's correction to a charge was dropped.
  - `ddb1e52` handles `modified` and `removed`.
  - In this run, the 8 pending charges that posted overnight were counted twice, and one $10 correction was lost. Together that adds up to $455.46.
- **Brute force.** `01d31d3` and `c3068ff` cap login attempts at 10 per IP and email pair. There are looser caps per IP and per email.
- **Login timing.** Before, an unknown email skipped the password hash, so it answered about 70 times faster. That tells an attacker which emails have accounts. `ab8c5ba` runs one bcrypt check either way.
- **Tests and lint.**
  - The tests are counted with `pytest --collect-only`. The original repo had no backend tests.
  - The lint count is `npx eslint .` on the old frontend, run with the same `package.json` as today. `1fb527f` fixed those errors, and CI now fails on any new ones.
- **Demo.** `/demo` signs the visitor into a throwaway account with 8 months of sample data, with no form to fill in (`ee8a009`, `3e277e7`).

## What the simulated bank is

`before_after.py` replaces only Plaid's HTTP client, with a fake that pages through an event log in pages of 100, which is Plaid's default. Everything else runs the real code, including its deliberate waits.

The fake bank holds:
- 8 months of history: 1,128 transactions across a checking account and a credit card;
- groceries, dining, rides, shopping, rent, subscriptions and twice-monthly pay;
- the last 8 card charges still pending.

"One day passes" then does three things:
- posts those 8 charges under new ids, adding a tip to one;
- adds 5 new purchases;
- changes one older charge by $10.

What this does not show: real Plaid latency, or how real users behave. Usage numbers come from the analytics in `docs/ANALYTICS.md` once real people use the app.

## Reproduce

```bash
createdb -O ci bench_before && createdb -O ci bench_after   # both get wiped
PYTHON=backend/.venv/bin/python scripts/benchmarks/run.sh
```

To measure one checkout on its own:

```bash
python scripts/benchmarks/before_after.py --backend <checkout>/backend \
  --database-url postgresql://ci:ci@localhost:5432/bench_after
```
