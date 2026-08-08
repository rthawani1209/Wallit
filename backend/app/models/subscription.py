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
    amount = Column(Numeric(12, 2), nullable=False)
    billing_interval = Column(String, nullable=False)  # 'weekly', 'monthly', 'annual'
    next_estimated_date = Column(Date, nullable=True)
    cheaper_alternative = Column(Text, nullable=True)
    # False once a detection run no longer sees this merchant recurring — kept (not
    # deleted) so the cheaper-alternative suggestion and history aren't lost.
    is_active = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="subscriptions")
