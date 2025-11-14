"""Inspection-related models for Production Inspection Bot."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum
from app.database import Base
from app.db.types import GUID, JSONBType


class MeetingStatus(str, Enum):
    """Inspection meeting status."""

    PENDING = "PENDING"  # Invitation sent, waiting for response
    ACCEPTED = "ACCEPTED"  # Accepted by accompanier
    DECLINED = "DECLINED"  # Declined by accompanier
    CONFIRMED = "CONFIRMED"  # Time confirmed by both parties
    CANCELLED = "CANCELLED"  # Cancelled by inspector
    COMPLETED = "COMPLETED"  # Inspection completed


class InspectionMeeting(Base):
    """Model for scheduling inspection meetings between inspector and accompanier."""

    __tablename__ = "inspection_meetings"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    check_instance_id = Column(GUID(), ForeignKey("check_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    inspector_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    accompanier_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    proposed_time = Column(DateTime(timezone=True), nullable=False)  # Time proposed by inspector
    confirmed_time = Column(DateTime(timezone=True), nullable=True)  # Time confirmed by both parties
    status = Column(SQLEnum(MeetingStatus), default=MeetingStatus.PENDING, nullable=False, index=True)
    message = Column(Text, nullable=True)  # Message from inspector
    accompanier_response = Column(Text, nullable=True)  # Response from accompanier
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    check_instance = relationship("CheckInstance", back_populates="meetings")
    inspector = relationship("User", foreign_keys=[inspector_id])
    accompanier = relationship("User", foreign_keys=[accompanier_id])


class ReferencePhoto(Base):
    """Model for reference photos (knowledge base) showing correct state."""

    __tablename__ = "reference_photos"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    department_id = Column(String(255), nullable=True, index=True)  # Department/area identifier
    checklist_item_id = Column(String(255), nullable=True, index=True)  # Checklist item/question ID
    template_id = Column(GUID(), ForeignKey("checklist_templates.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_key = Column(String(512), nullable=False)  # S3 key for the photo
    thumbnail_key = Column(String(512), nullable=True)  # S3 key for thumbnail
    meta_data = Column(JSONBType(), nullable=True, default=dict)  # Additional metadata (renamed from metadata to avoid SQLAlchemy conflict)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_by = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    template = relationship("ChecklistTemplate")


class ViolationFollowUp(Base):
    """Model for tracking violation follow-up tasks for next inspector."""

    __tablename__ = "violation_follow_ups"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    source_check_id = Column(GUID(), ForeignKey("check_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    target_check_id = Column(GUID(), ForeignKey("check_instances.id", ondelete="SET NULL"), nullable=True, index=True)
    department_id = Column(String(255), nullable=False, index=True)
    checklist_item_id = Column(String(255), nullable=False, index=True)  # Item/question where violation was found
    violation_description = Column(Text, nullable=False)
    violation_photo_keys = Column(JSONBType(), nullable=True, default=list)  # Photos of violation
    is_critical = Column(Boolean, default=False, nullable=False, index=True)
    status = Column(String(50), nullable=False, default="PENDING", index=True)  # PENDING, VERIFIED, RESOLVED, IGNORED
    assigned_to_inspector_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_photo_keys = Column(JSONBType(), nullable=True, default=list)  # Photos showing resolution
    resolution_comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    source_check = relationship("CheckInstance", foreign_keys=[source_check_id])
    target_check = relationship("CheckInstance", foreign_keys=[target_check_id])
    assigned_to_inspector = relationship("User", foreign_keys=[assigned_to_inspector_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])


class InspectionConfirmation(Base):
    """Model for accompanier confirmation of inspection completion."""

    __tablename__ = "inspection_confirmations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    check_instance_id = Column(GUID(), ForeignKey("check_instances.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    accompanier_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)
    inspector_confirmed = Column(Boolean, default=False, nullable=False)  # Confirms inspector identity
    inspection_confirmed = Column(Boolean, default=False, nullable=False)  # Confirms inspection took place
    confirmation_time = Column(DateTime(timezone=True), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    check_instance = relationship("CheckInstance", back_populates="confirmation")
    accompanier = relationship("User", foreign_keys=[accompanier_id])

