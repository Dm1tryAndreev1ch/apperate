"""Webhook service for sending events to subscribers."""
import httpx
import hmac
import hashlib
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
from app.models.webhook import WebhookSubscription, WebhookEvent
from app.crud.webhook import webhook

# Create async engine for webhook service
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class WebhookService:
    """Service for sending webhooks."""

    @staticmethod
    def _generate_signature(payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        return hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _send_webhook(url: str, payload: Dict[str, Any], secret: Optional[str] = None) -> Dict[str, Any]:
        """Send webhook with retry logic."""
        payload_str = json.dumps(payload, default=str)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "QualityControl-Webhook/1.0",
        }

        # Add signature if secret is provided
        if secret:
            signature = WebhookService._generate_signature(payload_str, secret)
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return {
                    "status": "success",
                    "status_code": response.status_code,
                    "response": response.text[:500],  # Limit response size
                }
        except httpx.HTTPError as e:
            return {
                "status": "error",
                "error": str(e),
            }

    @staticmethod
    async def send_event(
        event: WebhookEvent,
        payload: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Send webhook event to all active subscribers."""
        async with AsyncSessionLocal() as db:
            # Get all active webhooks for this event
            subscriptions = await webhook.get_by_event(db, event=event, active_only=True)
            
            results = []
            for subscription in subscriptions:
                # Prepare webhook payload
                webhook_payload = {
                    "event": event.value,
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": payload,
                }

                # Send webhook
                result = WebhookService._send_webhook(
                    subscription.url,
                    webhook_payload,
                    subscription.secret,
                )

                # Update subscription status
                subscription.last_status = result.get("status", "unknown")
                subscription.last_called_at = datetime.utcnow()
                db.add(subscription)

                results.append({
                    "webhook_id": str(subscription.id),
                    "url": subscription.url,
                    "result": result,
                })

            await db.commit()
            return results

    @staticmethod
    async def send_check_created(check_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Send check.created event."""
        return await WebhookService.send_event(WebhookEvent.CHECK_CREATED, check_data)

    @staticmethod
    async def send_check_completed(check_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Send check.completed event."""
        return await WebhookService.send_event(WebhookEvent.CHECK_COMPLETED, check_data)

    @staticmethod
    async def send_report_ready(report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Send report.ready event."""
        return await WebhookService.send_event(WebhookEvent.REPORT_READY, report_data)

    @staticmethod
    async def send_task_created(task_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Send task.created event."""
        return await WebhookService.send_event(WebhookEvent.TASK_CREATED, task_data)


webhook_service = WebhookService()

