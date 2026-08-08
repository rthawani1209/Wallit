import uuid

from pydantic import BaseModel


class AccountResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    current_balance: float | None

    class Config:
        from_attributes = True
