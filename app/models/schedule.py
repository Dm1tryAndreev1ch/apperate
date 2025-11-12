"""Schedule model."""
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Schedule(Base):
    """Schedule model for automated check creation."""

    __tablename__ = "schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Template to use for checks
    cron_or_rrule = Column(String(255), nullable=False)  # Cron expression or RRULE
    assigned_user_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)  # Array of user UUIDs
    auto_replace_on_absence = Column(Boolean, default=False, nullable=False)
    timezone = Column(String(50), nullable=False, default="UTC")
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

