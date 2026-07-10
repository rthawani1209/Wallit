import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class LinkedIdentity(Base):
    """One external login method linked to a User — e.g. their Google or Apple account.

    A single User can have several of these (password auth lives directly on
    User.password_hash and doesn't need a row here).
    """

    __tablename__ = "linked_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_provider_identity"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String, nullable=False)  # 'google', 'apple', etc.
    provider_user_id = Column(String, nullable=False)  # the provider's unique ID for this user
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="linked_identities")
