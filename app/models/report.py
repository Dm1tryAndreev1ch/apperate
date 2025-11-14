"""Report model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum
from app.database import Base
from app.db.types import GUID, JSONBType


class ReportFormatXLSX(str, Enum):
    """Single supported report format."""

    XLSX = "xlsx"


class ReportStatus(str, Enum):
    """Report status."""

    GENERATING = "GENERATING"
    READY = "READY"
    FAILED = "FAILED"


class Report(Base):
    """Report model."""

    __tablename__ = "reports"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    check_instance_id = Column(GUID(), ForeignKey("check_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    format = Column(SQLEnum(ReportFormatXLSX), nullable=False, index=True)
    file_key = Column(String(512), nullable=True)  # S3 key
    status = Column(SQLEnum(ReportStatus), default=ReportStatus.GENERATING, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    metadata_json = Column("metadata", JSONBType(), nullable=False, default=dict)

    # Relationships
    check_instance = relationship("CheckInstance", back_populates="reports")
    author = relationship("User", foreign_keys=[author_id], back_populates="authored_reports", lazy="joined")
    tasks = relationship("TaskLocal", back_populates="report", cascade="all, delete-orphan")
    generation_events = relationship(
        "ReportGenerationEvent",
        back_populates="report",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

