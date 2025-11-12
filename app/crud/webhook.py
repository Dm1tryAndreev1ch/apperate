"""Webhook CRUD operations."""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.webhook import WebhookSubscription, WebhookEvent


class CRUDWebhook(CRUDBase[WebhookSubscription, dict, dict]):
    """CRUD operations for WebhookSubscription."""

    async def get_by_event(
        self,
        db: AsyncSession,
        *,
        event: WebhookEvent,
        active_only: bool = True,
    ):
        """Get webhooks by event."""
        query = select(WebhookSubscription).where(WebhookSubscription.event == event)
        if active_only:
            query = query.where(WebhookSubscription.active == True)
        result = await db.execute(query)
        return result.scalars().all()


webhook = CRUDWebhook(WebhookSubscription)

