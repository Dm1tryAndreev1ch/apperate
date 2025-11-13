"""Webhook subscription model."""
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
import uuid
from enum import Enum
from app.database import Base
from app.db.types import GUID


class WebhookEvent(str, Enum):
    """Webhook event types."""

    CHECK_CREATED = "check.created"
    CHECK_COMPLETED = "check.completed"
    REPORT_READY = "report.ready"
    TASK_CREATED = "task.created"


class WebhookSubscription(Base):
    """Webhook subscription model."""

    __tablename__ = "webhook_subscriptions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    event = Column(SQLEnum(WebhookEvent), nullable=False, index=True)
    url = Column(String(512), nullable=False)
    secret = Column(String(255), nullable=True)  # Secret for webhook signature
    active = Column(Boolean, default=True, nullable=False, index=True)
    last_status = Column(String(50), nullable=True)  # Last delivery status
    last_called_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

