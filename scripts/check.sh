#!/usr/bin/env bash
# Runs the same steps as .github/workflows/ci.yml. Run it before every push.
#
# Needs a local Postgres you don't mind wiping. Point TEST_DATABASE_URL at it, e.g.
#   createuser -s ci && createdb -O ci ci   (password "ci")
#   TEST_DATABASE_URL=postgresql://ci:ci@localhost:5432/ci scripts/check.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
export DATABASE_URL="${TEST_DATABASE_URL:-postgresql://ci:ci@localhost:5432/ci}"
export JWT_SECRET_KEY="ci-only-secret-not-used-anywhere-real"
export ENCRYPTION_KEY="JCFWz8YjTTWCN32T0OFOPn4zpLM6pETHafofeIjGnjY="

step() { printf '\n== %s\n' "$1"; }

step "frontend: lint"
cd "$ROOT/frontend"
[ -d node_modules ] || npm ci
npx eslint .

step "frontend: typecheck"
npx tsc --noEmit

step "frontend: build"
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build >/dev/null

cd "$ROOT/backend"
step "backend: import check"
"$PYTHON" -c "import app.main"

step "backend: migrations on a fresh database"
"$PYTHON" - <<'PY'
import os
from sqlalchemy import create_engine, text

with create_engine(os.environ["DATABASE_URL"]).begin() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
PY
"$PYTHON" -m alembic upgrade head

step "backend: tests"
"$PYTHON" -m pytest -q

printf '\nAll checks passed.\n'
