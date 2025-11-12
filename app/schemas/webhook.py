"""Webhook schemas."""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from app.models.webhook import WebhookEvent


class WebhookSubscriptionBase(BaseModel):
    """Base webhook subscription schema."""

    event: WebhookEvent
    url: str
    secret: Optional[str] = None
    active: bool = True


class WebhookSubscriptionCreate(WebhookSubscriptionBase):
    """Webhook subscription creation schema."""

    pass


class WebhookSubscriptionUpdate(BaseModel):
    """Webhook subscription update schema."""

    url: Optional[str] = None
    secret: Optional[str] = None
    active: Optional[bool] = None


class WebhookSubscriptionResponse(WebhookSubscriptionBase):
    """Webhook subscription response schema."""

    id: UUID
    last_status: Optional[str] = None
    last_called_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

