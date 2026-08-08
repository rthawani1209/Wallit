import uuid
from sqlalchemy import Boolean, Column, String, Numeric, Date, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("user_id", "merchant_name", name="uq_subscriptions_user_merchant"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    transaction_pattern_id = Column(String, nullable=True)
    merchant_name = Column(String, nullable=False)
    # The category of the most recent matching charge — used to tell a genuine
    # discretionary subscription (Netflix, gym) apart from a recurring bill/debt
    # payment (rent, loan) for pages that only want to show one or the other.
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True)
    amount = Column(Numeric(12, 2), nullable=False)
    billing_interval = Column(String, nullable=False)  # 'weekly', 'monthly', 'annual'
    next_estimated_date = Column(Date, nullable=True)
    cheaper_alternative = Column(Text, nullable=True)
    # False once a detection run no longer sees this merchant recurring — kept (not
    # deleted) so the cheaper-alternative suggestion and history aren't lost.
    is_active = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="subscriptions")
    category = relationship("Category")
