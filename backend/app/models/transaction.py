import uuid
from sqlalchemy import Column, String, Numeric, Date, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False, index=True)
    plaid_transaction_id = Column(String, unique=True, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    merchant_name = Column(String, nullable=True)
    date = Column(Date, nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=True, index=True)
    is_subscription = Column(Boolean, default=False, nullable=False)
    is_anomaly = Column(Boolean, default=False, nullable=False)

    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    plan = relationship("Plan", back_populates="transactions")


# Composite index for the common "recent transactions for an account" query
Index("ix_transactions_account_date", Transaction.account_id, Transaction.date)
