import uuid
from sqlalchemy import Column, String, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String, nullable=False)  # 'trip', 'event', 'purchase', 'savings_goal'
    name = Column(String, nullable=False)
    target_amount = Column(Numeric(12, 2), nullable=False)
    target_date = Column(Date, nullable=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="plans")
    line_items = relationship("PlanLineItem", back_populates="plan", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="plan")


class PlanLineItem(Base):
    __tablename__ = "plan_line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=False, index=True)
    label = Column(String, nullable=False)
    estimated_amount = Column(Numeric(12, 2), nullable=False)
    actual_amount = Column(Numeric(12, 2), nullable=True)

    plan = relationship("Plan", back_populates="line_items")
