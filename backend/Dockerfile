FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (separate layer so Docker caches this unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command — overridden by docker-compose for dev (adds --reload).
# This is what actually runs in production (Railway etc): apply any pending
# migrations, then start the server. $PORT falls back to 8000 if a platform
# doesn't inject one (Railway does; plain `docker run` doesn't).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
