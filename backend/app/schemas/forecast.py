from datetime import date

from pydantic import BaseModel


class ForecastEvent(BaseModel):
    name: str
    amount: float


class ForecastDay(BaseModel):
    date: date
    balance: float
    events: list[ForecastEvent]


class ForecastResponse(BaseModel):
    starting_balance: float
    safe_to_spend: float
    next_payday: date | None
    low_point: ForecastDay
    daily_variable_spend: float
    days: list[ForecastDay]
