"""Audit log model."""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database import Base


class AuditLog(Base):
    """Audit log model for tracking all actions."""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    entity = Column(String(100), nullable=False, index=True)  # Entity type (e.g., "user", "checklist", "report")
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # Action type (e.g., "create", "update", "delete")
    diff = Column(JSONB, nullable=True)  # Changes made
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

