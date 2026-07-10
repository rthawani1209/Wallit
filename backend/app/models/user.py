import uuid
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    # Nullable — a user who signed up via Google/Apple has no local password
    password_hash = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Plaid access token stored encrypted — never log this field
    plaid_access_token = Column(Text, nullable=True)

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan")
    bills = relationship("Bill", back_populates="user", cascade="all, delete-orphan")
    linked_identities = relationship("LinkedIdentity", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
