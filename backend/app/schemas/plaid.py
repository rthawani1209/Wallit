from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LinkTokenResponse(BaseModel):
    link_token: str


class ExchangeTokenRequest(BaseModel):
    public_token: str
    # From Plaid Link's onSuccess metadata, so the UI can say which bank is which.
    institution_name: str | None = None


class PlaidItemResponse(BaseModel):
    id: UUID
    institution_name: str | None
    account_count: int
    last_synced_at: datetime | None
