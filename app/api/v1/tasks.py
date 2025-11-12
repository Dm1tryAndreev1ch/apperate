"""Tasks API endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import User
from app.core.security import Permission
from app.crud.task import task
from app.crud.report import report
from app.schemas.task import TaskLocalCreate, TaskLocalResponse
from app.core.exceptions import NotFoundError
from app.tasks.bitrix import sync_task_to_bitrix
from app.services.webhook_service import webhook_service

router = APIRouter()


@router.post("/from_report", response_model=TaskLocalResponse, status_code=status.HTTP_201_CREATED)
async def create_task_from_report(
    report_id: UUID,
    title: str,
    description: str = "",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.INTEGRATION_MANAGE)),
):
    """Create a local task from a report."""
    # Verify report exists
    report_obj = await report.get(db, id=report_id)
    if not report_obj:
        raise NotFoundError("Report not found")

    # Create task
    task_data = TaskLocalCreate(
        report_id=report_id,
        title=title,
        description=description,
        status="PENDING",
    )
    new_task = await task.create(db, obj_in=task_data)

    # Queue sync to Bitrix
    sync_task_to_bitrix.delay(str(new_task.id))

    # Send webhook event (fire and forget)
    try:
        await webhook_service.send_task_created({
            "task_id": str(new_task.id),
            "report_id": str(report_id),
            "title": title,
        })
    except Exception:
        pass  # Don't fail request if webhook fails

    return new_task

