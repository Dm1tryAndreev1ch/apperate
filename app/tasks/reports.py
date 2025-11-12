"""Celery tasks for report generation."""
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.tasks.celery_app import celery_app
from app.config import settings
from app.models.report import Report, ReportStatus, ReportFormat
from app.models.checklist import CheckInstance
from app.models.user import User
from app.services.report_service import report_service
from app.services.webhook_service import webhook_service
from tenacity import retry, stop_after_attempt, wait_exponential

# Create async engine for Celery tasks
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(bind=True, max_retries=3)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def generate_report(self, report_id: str, formats: List[str] = None):
    """Generate report asynchronously."""
    if formats is None:
        formats = ["pdf"]

    async def _generate():
        async with AsyncSessionLocal() as db:
            # Get report
            result = await db.execute(select(Report).where(Report.id == UUID(report_id)))
            report_obj = result.scalar_one_or_none()
            if not report_obj:
                raise ValueError(f"Report {report_id} not found")

            # Get check instance
            result = await db.execute(select(CheckInstance).where(CheckInstance.id == report_obj.check_instance_id))
            check_instance = result.scalar_one_or_none()
            if not check_instance:
                raise ValueError(f"Check instance {report_obj.check_instance_id} not found")

            # Get template schema (simplified - should get from template)
            # For now, use schema from check_instance
            from app.crud.checklist import template
            template_obj = await template.get(db, id=check_instance.template_id)
            if not template_obj:
                raise ValueError("Template not found")

            # Get inspector name
            inspector_name = "Unknown"
            if check_instance.inspector_id:
                result = await db.execute(select(User).where(User.id == check_instance.inspector_id))
                inspector = result.scalar_one_or_none()
                if inspector:
                    inspector_name = inspector.full_name

            try:
                # Generate report for each format
                for format_str in formats:
                    format_enum = ReportFormat(format_str)
                    file_key = report_service.generate_and_upload(
                        check_instance,
                        template_obj.schema,
                        format_enum,
                        inspector_name,
                    )

                    # Update report
                    report_obj.file_key = file_key
                    report_obj.format = format_enum
                    report_obj.status = ReportStatus.READY
                    db.add(report_obj)

                await db.commit()
                
                # Send webhook event
                await webhook_service.send_report_ready({
                    "report_id": report_id,
                    "check_instance_id": str(report_obj.check_instance_id),
                    "format": format_str,
                    "file_key": file_key,
                })
            except Exception as e:
                report_obj.status = ReportStatus.FAILED
                db.add(report_obj)
                await db.commit()
                raise

    import asyncio
    asyncio.run(_generate())

