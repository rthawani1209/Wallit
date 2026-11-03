import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PlaidItem(Base):
    """One bank login connected through Plaid. A user can have several, and each
    keeps its own access token and sync cursor."""

    __tablename__ = "plaid_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    # Plaid's id for the item. Null only for banks linked before this table
    # existed, where we never stored it.
    item_id = Column(String, unique=True, nullable=True)
    # Encrypted, like every Plaid token. Never log it.
    access_token = Column(Text, nullable=False)
    institution_name = Column(String, nullable=True)
    # Where /transactions/sync left off. Null means the next sync is a full pull.
    cursor = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="plaid_items")
    accounts = relationship("Account", back_populates="plaid_item")
