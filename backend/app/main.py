from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import (
    accounts,
    auth,
    budgets,
    categories,
    chat,
    plaid,
    plans,
    simulate,
    subscriptions,
    transactions,
)
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Wallit API", version="0.1.0", lifespan=lifespan)

# CORS_ORIGINS in .env controls which frontend(s) can call this API.
# credentials=True is required so cookies (our JWT) are sent cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(plaid.router, prefix="/api/v1")
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(simulate.router, prefix="/api/v1")
app.include_router(budgets.router, prefix="/api/v1")
app.include_router(subscriptions.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(plans.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
