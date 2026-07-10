FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (separate layer so Docker caches this unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command — overridden by docker-compose for dev (adds --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
