import uuid
from sqlalchemy import Column, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Budget(Base):
    """A user-set monthly spending limit for a category. Absent rows fall back to
    an auto-suggested limit computed from historical spend (see routers/budgets.py)."""

    __tablename__ = "budgets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"), nullable=False)
    monthly_limit = Column(Numeric(12, 2), nullable=False)

    user = relationship("User", back_populates="budgets")
    category = relationship("Category")

    __table_args__ = (UniqueConstraint("user_id", "category_id", name="uq_budgets_user_category"),)
