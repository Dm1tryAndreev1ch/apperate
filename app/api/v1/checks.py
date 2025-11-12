"""Checks API endpoints."""
from typing import List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import User
from app.models.checklist import CheckInstance, CheckStatus
from app.core.security import Permission
from app.crud.checklist import check_instance, template
from app.crud.report import report
from app.crud.task import task
from app.services.checklist_service import checklist_service
from app.schemas.checklist import CheckInstanceCreate, CheckInstanceUpdate, CheckInstanceResponse
from app.schemas.report import ReportCreate
from app.schemas.task import TaskLocalCreate
from app.core.exceptions import NotFoundError, ValidationError
from app.tasks.reports import generate_report
from app.tasks.bitrix import sync_task_to_bitrix
from app.services.webhook_service import webhook_service

router = APIRouter()


@router.get("", response_model=List[CheckInstanceResponse])
async def list_checks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all check instances."""
    checks = await check_instance.get_multi(db, skip=skip, limit=limit)
    return checks


@router.post("", response_model=CheckInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_check(
    check_data: CheckInstanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CHECKLIST_CREATE)),
):
    """Create a new check instance."""
    # Verify template exists
    template_obj = await template.get(db, id=check_data.template_id)
    if not template_obj:
        raise NotFoundError("Template not found")

    check_dict = check_data.dict()
    check_dict["template_version"] = template_obj.version
    check_dict["inspector_id"] = current_user.id
    check_dict["status"] = CheckStatus.IN_PROGRESS
    check_dict["started_at"] = datetime.utcnow()

    new_check = await check_instance.create(db, obj_in=check_data)
    
    # Send webhook event (fire and forget)
    try:
        await webhook_service.send_check_created({
            "check_id": str(new_check.id),
            "template_id": str(check_data.template_id),
            "inspector_id": str(current_user.id),
        })
    except Exception:
        pass  # Don't fail request if webhook fails
    
    return new_check


@router.get("/{check_id}", response_model=CheckInstanceResponse)
async def get_check(
    check_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a check instance by ID."""
    check_obj = await check_instance.get(db, id=check_id)
    if not check_obj:
        raise NotFoundError("Check not found")
    return check_obj


@router.patch("/{check_id}", response_model=CheckInstanceResponse)
async def update_check(
    check_id: UUID,
    check_data: CheckInstanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Partially update a check instance (save progress)."""
    check_obj = await check_instance.get(db, id=check_id)
    if not check_obj:
        raise NotFoundError("Check not found")

    # Validate answers if provided
    if check_data.answers is not None:
        template_obj = await template.get(db, id=check_obj.template_id)
        is_valid, errors = checklist_service.validate_answers(template_obj.schema, check_data.answers)
        if not is_valid:
            raise ValidationError(f"Validation errors: {', '.join(errors)}")

    updated_check = await check_instance.update(db, db_obj=check_obj, obj_in=check_data)
    return updated_check


@router.post("/{check_id}/complete", response_model=CheckInstanceResponse)
async def complete_check(
    check_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CHECKLIST_COMPLETE)),
):
    """Complete a check instance - generates report and creates tasks if needed."""
    check_obj = await check_instance.get(db, id=check_id)
    if not check_obj:
        raise NotFoundError("Check not found")

    if check_obj.status == CheckStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Check already completed")

    # Get template for validation
    template_obj = await template.get(db, id=check_obj.template_id)
    if not template_obj:
        raise NotFoundError("Template not found")

    # Validate answers
    is_valid, errors = checklist_service.validate_answers(template_obj.schema, check_obj.answers)
    if not is_valid:
        raise ValidationError(f"Validation errors: {', '.join(errors)}")

    # Update check status
    check_obj.status = CheckStatus.COMPLETED
    check_obj.finished_at = datetime.utcnow()
    db.add(check_obj)

    # Create report
    report_data = ReportCreate(
        check_instance_id=check_id,
        format="pdf",
    )
    new_report = await report.create(db, obj_in=report_data)
    new_report.generated_by = current_user.id
    db.add(new_report)

    # Check for critical violations and create tasks
    violations = checklist_service.find_critical_violations(template_obj.schema, check_obj.answers)
    if violations:
        task_data = TaskLocalCreate(
            report_id=new_report.id,
            title=f"Critical violations in check {check_id}",
            description=f"Found {len(violations)} critical violations",
            status="PENDING",
        )
        new_task = await task.create(db, obj_in=task_data)
        # Queue sync to Bitrix
        sync_task_to_bitrix.delay(str(new_task.id))

    await db.commit()
    await db.refresh(check_obj)

    # Queue report generation
    generate_report.delay(str(new_report.id), formats=["pdf"])

    # Send webhook event (fire and forget)
    try:
        await webhook_service.send_check_completed({
            "check_id": str(check_id),
            "report_id": str(new_report.id),
            "violations_count": len(violations),
        })
    except Exception:
        pass  # Don't fail request if webhook fails

    return check_obj

