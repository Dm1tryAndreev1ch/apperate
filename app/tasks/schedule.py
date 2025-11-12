"""Celery tasks for scheduled checks."""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from datetime import datetime
from uuid import UUID
from app.tasks.celery_app import celery_app
from app.config import settings
from app.models.schedule import Schedule
from app.models.checklist import CheckInstance, CheckStatus
from app.models.checklist import ChecklistTemplate
from app.crud.checklist import check_instance
from app.schemas.checklist import CheckInstanceCreate
from app.models.checklist import TemplateStatus

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

            # Verify template exists
            if not schedule.template_id:
                return  # Cannot create checks without template

            result = await db.execute(
                select(ChecklistTemplate).where(ChecklistTemplate.id == schedule.template_id)
            )
            template = result.scalar_one_or_none()
            if not template or template.status != TemplateStatus.ACTIVE:
                return  # Template not found or not active

            # Create check instances for assigned users
            if schedule.assigned_user_ids:
                for user_id in schedule.assigned_user_ids:
                    # Check if there's an incomplete check for this user and schedule
                    if schedule.auto_replace_on_absence:
                        # Find incomplete checks for this user and template
                        result = await db.execute(
                            select(CheckInstance).where(
                                CheckInstance.inspector_id == user_id,
                                CheckInstance.template_id == schedule.template_id,
                                CheckInstance.status == CheckStatus.IN_PROGRESS,
                            )
                        )
                        existing_check = result.scalar_one_or_none()
                        if existing_check:
                            continue  # Skip if there's already an incomplete check

                    # Create new check instance
                    check_data = CheckInstanceCreate(
                        template_id=schedule.template_id,
                        scheduled_at=datetime.utcnow(),
                        inspector_id=user_id,
                    )
                    new_check = await check_instance.create(db, obj_in=check_data)
                    
                    # Update with additional fields
                    new_check.template_version = template.version
                    new_check.status = CheckStatus.IN_PROGRESS
                    new_check.started_at = datetime.utcnow()
                    db.add(new_check)

            await db.commit()

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
                # Check if schedule should run now (simplified - in production use cron parser)
                # For now, we'll let Celery Beat handle the timing via beat_schedule
                schedule_create_checks.delay(str(schedule.id))

    import asyncio
    asyncio.run(_process())
