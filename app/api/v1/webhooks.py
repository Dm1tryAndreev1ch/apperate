"""Webhooks API endpoints (Admin)."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import User
from app.core.security import Permission
from app.crud.webhook import webhook
from app.schemas.webhook import WebhookSubscriptionCreate, WebhookSubscriptionUpdate, WebhookSubscriptionResponse
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("", response_model=List[WebhookSubscriptionResponse])
async def list_webhooks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.WEBHOOK_VIEW)),
):
    """List all webhook subscriptions."""
    webhooks = await webhook.get_multi(db, skip=skip, limit=limit)
    return webhooks


@router.post("", response_model=WebhookSubscriptionResponse, status_code=201)
async def create_webhook(
    webhook_data: WebhookSubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.WEBHOOK_CREATE)),
):
    """Create a new webhook subscription."""
    new_webhook = await webhook.create(db, obj_in=webhook_data.dict())
    return new_webhook


@router.get("/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def get_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.WEBHOOK_VIEW)),
):
    """Get a webhook subscription by ID."""
    webhook_obj = await webhook.get(db, id=webhook_id)
    if not webhook_obj:
        raise NotFoundError("Webhook not found")
    return webhook_obj


@router.put("/{webhook_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook(
    webhook_id: UUID,
    webhook_data: WebhookSubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.WEBHOOK_UPDATE)),
):
    """Update a webhook subscription."""
    webhook_obj = await webhook.get(db, id=webhook_id)
    if not webhook_obj:
        raise NotFoundError("Webhook not found")
    updated_webhook = await webhook.update(db, db_obj=webhook_obj, obj_in=webhook_data)
    return updated_webhook


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(
    webhook_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.WEBHOOK_DELETE)),
):
    """Delete a webhook subscription."""
    webhook_obj = await webhook.get(db, id=webhook_id)
    if not webhook_obj:
        raise NotFoundError("Webhook not found")
    await webhook.remove(db, id=webhook_id)

