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
    actual_spend: float
    projected_spend: float
    projected_balance: float


class CashFlowMonth(BaseModel):
    month: str  # "2026-02"
    label: str  # "Feb"
    income: float
    expenses: float


class BudgetProgress(BaseModel):
    category_id: uuid.UUID
    category_name: str
    limit: float
    spent: float
    is_custom: bool  # whether this reflects a user-set limit vs an auto-suggested one


class BudgetSetRequest(BaseModel):
    limit: float


class UpcomingBill(BaseModel):
    merchant_name: str
    amount: float
    next_due_date: date
