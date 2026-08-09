# Deploying Wallit

Frontend on Vercel, backend + Postgres on Railway. Both support deploying straight
from this GitHub repo, and both auto-deploy on every push to `main` once connected —
that's the "continuous deployment" part; the CI workflow in `.github/workflows/ci.yml`
is what gates it (a failing typecheck/build/migration blocks the deploy).

## 1. Backend + Postgres on Railway

1. New Project → Deploy from GitHub repo → select this repo.
2. Add a Postgres database from Railway's template picker (one click) — this becomes
   its own service in the project with its own `DATABASE_URL`.
3. Add a second service for the backend: "Deploy from repo" again, but set **Root
   Directory** to `backend`. Railway will detect `backend/Dockerfile` and build from
   it — the Dockerfile already runs migrations automatically on every start (see
   its `CMD`), so there's no separate migration step to remember.
4. On the backend service, set these environment variables:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Reference Railway's Postgres variable: `${{Postgres.DATABASE_URL}}` |
   | `ENVIRONMENT` | `production` |
   | `CORS_ORIGINS` | your Vercel URL, e.g. `https://wallit.vercel.app` (set after step 2 below) |
   | `JWT_SECRET_KEY` | a new random secret — **don't reuse the dev one**. Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
   | `ENCRYPTION_KEY` | a new Fernet key — **don't reuse the dev one**. Generate with `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
   | `PLAID_CLIENT_ID` | from your Plaid dashboard |
   | `PLAID_SECRET` | your **production** secret once you're off sandbox |
   | `PLAID_ENV` | `sandbox` until you're ready, then `production` |
   | `ANTHROPIC_API_KEY` | your Anthropic key |
   | `GOOGLE_PLACES_API_KEY` | your Google Places key |
   | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | from Google Cloud Console |
   | `GOOGLE_REDIRECT_URI` | `https://<your-railway-backend-domain>/api/v1/auth/google/callback` |
   | `FRONTEND_URL` | your Vercel URL — used to redirect back after Google login |

   Also add your Railway backend's own domain as an **authorized redirect URI** in
   the Google Cloud Console OAuth client, or Google sign-in will fail.

5. Deploy. Railway gives you a domain like `wallit-backend-production.up.railway.app`
   — note it, you'll need it for Vercel's env vars next.

## 2. Frontend on Vercel

1. Import this GitHub repo as a new Vercel project.
2. Set **Root Directory** to `frontend` (Vercel auto-detects Next.js once you do).
3. Environment variable:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | your Railway backend URL from step 1.5 above |

4. Deploy. Vercel gives you a domain like `wallit.vercel.app`.

## 3. Close the loop

Now that both are live, go back and:
- Set Railway's `CORS_ORIGINS` and `FRONTEND_URL` to the real Vercel URL (if you
  hadn't yet).
- Add the Vercel URL as an authorized JavaScript origin in Google Cloud Console.
- Redeploy the backend so the new env vars take effect.

At that point login, Plaid Link, and Google sign-in should all work against the
live URLs exactly like they do locally.

## 4. Going to a real bank (production Plaid)

Sandbox → production is just swapping `PLAID_CLIENT_ID`/`PLAID_SECRET` for the
production ones from your Plaid dashboard and setting `PLAID_ENV=production` —
no code changes. Do this once you've confirmed the free-tier limits and
Limited Production terms in the Plaid dashboard work for your plan.
