"""Schedule model."""
import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base
from app.db.types import GUID, UUIDArray


class Schedule(Base):
    """Schedule model for automated check creation."""

    __tablename__ = "schedules"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    template_id = Column(GUID(), nullable=True, index=True)  # Template to use for checks
    cron_or_rrule = Column(String(255), nullable=False)  # Cron expression or RRULE
    assigned_user_ids = Column(UUIDArray(), nullable=True)  # Deprecated: inspector pool
    inspector_pool = Column(UUIDArray(), nullable=True)  # Array of eligible inspectors
    brigade_pool = Column(UUIDArray(), nullable=True)  # Array of brigades to rotate through
    last_inspector_index = Column(Integer, nullable=False, default=0)
    last_brigade_index = Column(Integer, nullable=False, default=0)
    auto_replace_on_absence = Column(Boolean, default=False, nullable=False)
    timezone = Column(String(50), nullable=False, default="UTC")
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

