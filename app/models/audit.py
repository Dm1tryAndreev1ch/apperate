"""Audit log model."""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.sql import func
import uuid
from app.database import Base
from app.db.types import JSONBType, GUID


class AuditLog(Base):
    """Audit log model for tracking all actions."""

    __tablename__ = "audit_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    entity = Column(String(100), nullable=False, index=True)  # Entity type (e.g., "user", "checklist", "report")
    entity_id = Column(GUID(), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # Action type (e.g., "create", "update", "delete")
    diff = Column(JSONBType(), nullable=True)  # Changes made
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

