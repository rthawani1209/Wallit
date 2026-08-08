import uuid
from datetime import date

from pydantic import BaseModel


class TransactionResponse(BaseModel):
    id: uuid.UUID
    amount: float
    merchant_name: str | None
    date: date
    category_id: uuid.UUID | None
    is_subscription: bool
    is_anomaly: bool

    class Config:
        from_attributes = True


class TransactionUpdateRequest(BaseModel):
    category_id: uuid.UUID


class CategorySpend(BaseModel):
    category_id: uuid.UUID | None
    category_name: str
    total: float


class SimulateResponse(BaseModel):
    current_balance: float
    actual_month_spend: float
    projected_month_spend: float
    projected_balance: float
