import uuid
from sqlalchemy import Column, String, Numeric, Date, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_pattern_id = Column(String, nullable=True)
    merchant_name = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    billing_interval = Column(String, nullable=False)  # 'monthly', 'annual', etc.
    next_estimated_date = Column(Date, nullable=True)
    cheaper_alternative = Column(Text, nullable=Trclaue)
