import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str
    last_name: str
    date_of_birth: date

    @field_validator("first_name", "last_name")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def reasonable_birthday(cls, v: date) -> date:
        today = date.today()
        if v >= today:
            raise ValueError("date of birth must be in the past")
        age_years = (today - v).days / 365.25
        if age_years < 18:
            raise ValueError("must be at least 18 years old")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None

    class Config:
        from_attributes = True