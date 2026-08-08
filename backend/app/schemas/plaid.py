import uuid
from datetime import date

from pydantic import BaseModel


class LinkTokenResponse(BaseModel):
    link_token: str


class ExchangeTokenRequest(BaseModel):
    public_token: str


class AccountResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    current_balance: float | None

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    id: uuid.UUID
    amount: float
    merchant_name: str | None
    date: date
    is_subscription: bool
    is_anomaly: bool

    class Config:
        from_attributes = True