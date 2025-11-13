"""Checklist models."""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum
from app.database import Base
from app.db.types import JSONBType, GUID


class TemplateStatus(str, Enum):
    """Checklist template status."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class CheckStatus(str, Enum):
    """Check instance status."""

    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ChecklistTemplate(Base):
    """Checklist template model."""

    __tablename__ = "checklist_templates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    schema = Column(JSONBType(), nullable=False)  # Structure: sections → questions → {id, type, required, meta}
    status = Column(SQLEnum(TemplateStatus), default=TemplateStatus.ACTIVE, nullable=False, index=True)
    created_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    versions = relationship("ChecklistTemplateVersion", back_populates="template", cascade="all, delete-orphan")
    check_instances = relationship("CheckInstance", back_populates="template")


class ChecklistTemplateVersion(Base):
    """Checklist template version history."""

    __tablename__ = "checklist_template_versions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    template_id = Column(GUID(), ForeignKey("checklist_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, index=True)
    schema = Column(JSONBType(), nullable=False)
    diff = Column(JSONBType(), nullable=True)  # Differences from previous version
    created_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    template = relationship("ChecklistTemplate", back_populates="versions")


class CheckInstance(Base):
    """Check instance model."""

    __tablename__ = "check_instances"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    template_id = Column(GUID(), ForeignKey("checklist_templates.id", ondelete="RESTRICT"), nullable=False, index=True)
    template_version = Column(Integer, nullable=False)
    project_id = Column(String(255), nullable=True, index=True)
    department_id = Column(String(255), nullable=True, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    inspector_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    brigade_id = Column(GUID(), ForeignKey("brigades.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(SQLEnum(CheckStatus), default=CheckStatus.IN_PROGRESS, nullable=False, index=True)
    answers = Column(JSONBType(), nullable=False, default=dict)  # Answers to questions
    comments = Column(JSONBType(), nullable=True)  # Comments per question or general
    media_keys = Column(JSONBType(), nullable=True, default=list)  # Array of S3 keys for photos/files
    audit = Column(JSONBType(), nullable=True)  # Audit trail

    # Relationships
    template = relationship("ChecklistTemplate", back_populates="check_instances")
    inspector = relationship("User", foreign_keys=[inspector_id])
    brigade = relationship("Brigade", back_populates="checks")
    reports = relationship("Report", back_populates="check_instance", cascade="all, delete-orphan")

