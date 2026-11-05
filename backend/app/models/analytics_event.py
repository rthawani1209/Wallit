import uuid
from sqlalchemy import Boolean, Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.database import Base


class AnalyticsEvent(Base):
    """One thing someone did in the app, for usage numbers. See services/analytics.py.

    user_id is deliberately not a foreign key: demo accounts are deleted after a
    day, and their events should still count. Nothing here is personal or
    financial (no emails, amounts or merchant names)."""

    __tablename__ = "analytics_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(64), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    # Random id the browser keeps, so visits before sign-up can be counted.
    visitor_id = Column(String(64), nullable=True)
    is_demo = Column(Boolean, nullable=False, default=False)
    properties = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_analytics_events_name_created", "name", "created_at"),)
