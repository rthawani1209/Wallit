import uuid
from datetime import date

from pydantic import BaseModel


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    merchant_name: str
    amount: float
    billing_interval: str
    next_estimated_date: date | None
    category_name: str | None
    cheaper_alternative: str | None
    is_active: bool

    class Config:
        from_attributes = True


class CalendarEvent(BaseModel):
    date: date
    merchant_name: str
    amount: float
    category_name: str | None
    billing_interval: str


class AnomalyResponse(BaseModel):
    id: uuid.UUID
    merchant_name: str | None
    amount: float
    date: date
    category_name: str | None
    anomaly_reason: str | None

    class Config:
        from_attributes = True
