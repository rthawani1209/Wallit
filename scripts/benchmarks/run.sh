#!/usr/bin/env bash
# Runs before_after.py against the code before any of the recent work and
# against the current checkout, each on its own empty database.
#
#   createdb -O ci bench_before && createdb -O ci bench_after
#   PYTHON=path/to/venv/python scripts/benchmarks/run.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON="${PYTHON:-python3}"
BASELINE="${BASELINE:-70050e4}"  # last commit before the Oct 27 work started
DB="${BENCH_DB:-postgresql://ci:ci@localhost:5432}"
OLD="$(mktemp -d)/wallit-baseline"

git -C "$ROOT" worktree add --detach "$OLD" "$BASELINE" >/dev/null
trap 'git -C "$ROOT" worktree remove --force "$OLD"' EXIT

"$PYTHON" "$ROOT/scripts/benchmarks/before_after.py" --backend "$OLD/backend" \
  --database-url "$DB/bench_before" --label "before ($BASELINE)"
"$PYTHON" "$ROOT/scripts/benchmarks/before_after.py" --backend "$ROOT/backend" \
  --database-url "$DB/bench_after" --label "after ($(git -C "$ROOT" rev-parse --short HEAD))"
