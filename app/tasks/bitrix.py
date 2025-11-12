"""Celery tasks for Bitrix integration."""
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from datetime import datetime
from app.tasks.celery_app import celery_app
from app.config import settings
from app.models.task import TaskLocal
from app.integrations.bitrix import bitrix_integration
from tenacity import retry, stop_after_attempt, wait_exponential

# Create async engine for Celery tasks
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(bind=True, max_retries=3)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def sync_task_to_bitrix(self, task_id: str):
    """Sync task to Bitrix."""
    async def _sync():
        async with AsyncSessionLocal() as db:
            # Get task
            result = await db.execute(select(TaskLocal).where(TaskLocal.id == UUID(task_id)))
            task_obj = result.scalar_one_or_none()
            if not task_obj:
                raise ValueError(f"Task {task_id} not found")

            # Prepare payload
            payload = {
                "title": task_obj.title,
                "description": task_obj.description,
                "status": task_obj.status,
            }

            # Sync with Bitrix
            if task_obj.bitrix_id:
                # Update existing task
                response = bitrix_integration.update_task(task_obj.bitrix_id, payload)
            else:
                # Create new task
                response = bitrix_integration.create_task(payload)
                if response.get("ok") and response.get("external_id"):
                    task_obj.bitrix_id = response["external_id"]

            # Update last sync time
            task_obj.last_sync_at = datetime.utcnow()
            db.add(task_obj)
            await db.commit()

    import asyncio
    asyncio.run(_sync())

