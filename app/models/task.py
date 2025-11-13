"""Task model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base
from app.db.types import GUID


class TaskLocal(Base):
    """Local task model (can be synced with Bitrix)."""

    __tablename__ = "task_local"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    report_id = Column(GUID(), ForeignKey("reports.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    bitrix_id = Column(String(255), nullable=True, index=True)  # External Bitrix task ID
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    report = relationship("Report", back_populates="tasks")

