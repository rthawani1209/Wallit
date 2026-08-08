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
    # Plaid's own raw categorization, kept alongside our derived category_id so a
    # transaction can be recategorized later without re-fetching from Plaid.
    plaid_category_primary = Column(String, nullable=True)
    plaid_category_detailed = Column(String, nullable=True)
    # True once a user has manually picked a category for this transaction — a resync
    # should never silently overwrite that choice back to the auto-resolved category.
    category_is_manual = Column(Boolean, default=False, nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id"), nullable=True, index=True)
    is_subscription = Column(Boolean, default=False, nullable=False)
    is_anomaly = Column(Boolean, default=False, nullable=False)
    # Human-readable explanation for why this was flagged, e.g. "62% higher than your
    # typical Food spend" or "Netflix price increased from $15.99 to $19.99".
    anomaly_reason = Column(String, nullable=True)

    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
    plan = relationship("Plan", back_populates="transactions")


# Composite index for the common "recent transactions for an account" query
Index("ix_transactions_account_date", Transaction.account_id, Transaction.date)
