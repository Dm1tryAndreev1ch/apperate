"""Notification models."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum
from app.database import Base
from app.db.types import GUID, JSONBType


class NotificationChannel(str, Enum):
    """Notification delivery channels."""

    EMAIL = "EMAIL"
    TELEGRAM = "TELEGRAM"
    WEB = "WEB"  # In-app notifications


class NotificationStatus(str, Enum):
    """Notification status."""

    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    READ = "READ"  # For web notifications


class NotificationType(str, Enum):
    """Notification types."""

    INSPECTION_ASSIGNED = "INSPECTION_ASSIGNED"
    INSPECTION_REMINDER = "INSPECTION_REMINDER"
    MEETING_INVITATION = "MEETING_INVITATION"
    MEETING_ACCEPTED = "MEETING_ACCEPTED"
    MEETING_DECLINED = "MEETING_DECLINED"
    VIOLATION_FOLLOWUP = "VIOLATION_FOLLOWUP"
    REPORT_READY = "REPORT_READY"
    ABSENCE_REPLACEMENT = "ABSENCE_REPLACEMENT"
    CONFIRMATION_REQUEST = "CONFIRMATION_REQUEST"


class Notification(Base):
    """Notification model."""

    __tablename__ = "notifications"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(SQLEnum(NotificationChannel), nullable=False, index=True)
    type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(SQLEnum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)
    meta_data = Column(JSONBType(), nullable=True, default=dict)  # Additional data (check_id, meeting_id, etc.) (renamed from metadata to avoid SQLAlchemy conflict)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")


class NotificationPreference(Base):
    """User notification preferences."""

    __tablename__ = "notification_preferences"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    # Channel preferences (JSONB: {EMAIL: {enabled: bool, time: "08:00"}, TELEGRAM: {...}, WEB: {...}})
    channel_preferences = Column(JSONBType(), nullable=False, default=dict)
    # Type preferences (JSONB: {INSPECTION_ASSIGNED: {enabled: bool, channels: [...]}, ...})
    type_preferences = Column(JSONBType(), nullable=False, default=dict)
    # Daily reminder time (HH:MM format)
    daily_reminder_time = Column(String(5), nullable=True)  # e.g., "08:00"
    daily_reminder_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="notification_preferences")

