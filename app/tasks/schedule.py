"""Celery tasks for scheduled checks."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from uuid import UUID
from app.tasks.celery_app import celery_app
from app.config import settings
from app.models.schedule import Schedule
from app.services.schedule_service import schedule_service

# Create async engine for Celery tasks
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task
def schedule_create_checks(schedule_id: str):
    """Create check instances based on schedule."""
    async def _create():
        async with AsyncSessionLocal() as db:
            # Get schedule
            result = await db.execute(select(Schedule).where(Schedule.id == UUID(schedule_id)))
            schedule = result.scalar_one_or_none()
            if not schedule or not schedule.enabled:
                return

            await schedule_service.spawn_check(db, schedule)

    import asyncio
    asyncio.run(_create())


@celery_app.task
def process_all_schedules():
    """Process all enabled schedules (called by Celery Beat)."""
    async def _process():
        async with AsyncSessionLocal() as db:
            # Get all enabled schedules
            result = await db.execute(
                select(Schedule).where(Schedule.enabled == True)
            )
            schedules = result.scalars().all()

            for schedule in schedules:
                schedule_create_checks.delay(str(schedule.id))

    import asyncio
    asyncio.run(_process())
