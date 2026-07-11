from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, plaid

app = FastAPI(title="Wallit API", version="0.1.0")

# Allow the Next.js frontend (running on port 3000) to call this API.
# credentials=True is required so cookies (our JWT) are sent cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(plaid.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}
