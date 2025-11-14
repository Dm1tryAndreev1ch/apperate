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
from app.crud.brigade import brigade_score
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
from app.routing.encrypted_route import EncryptedAPIRoute

router = APIRouter(route_class=EncryptedAPIRoute)


@router.get("", response_model=List[CheckInstanceResponse])
async def list_checks(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all check instances."""
    try:
        checks = await check_instance.get_multi(db, skip=skip, limit=limit)
        return checks
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при получении списка чек-листов: {str(e)}"
        )


@router.post("", response_model=CheckInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_check(
    check_data: CheckInstanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.CHECKLIST_CREATE)),
):
    """Create a new check instance."""
    try:
        # Verify template exists
        template_obj = await template.get(db, id=check_data.template_id)
        if not template_obj:
            raise NotFoundError("Template not found")

        if hasattr(check_data, "model_dump"):
            payload = check_data.model_dump(exclude_unset=True, mode="python")
        else:
            payload = check_data.dict(exclude_unset=True)
        payload["template_version"] = template_obj.version
        payload["inspector_id"] = payload.get("inspector_id") or current_user.id
        payload.setdefault("status", CheckStatus.IN_PROGRESS)
        if payload.get("status") == CheckStatus.IN_PROGRESS and payload.get("started_at") is None:
            scheduled_at = payload.get("scheduled_at")
            should_start_now = True
            if isinstance(scheduled_at, datetime):
                scheduled_naive = scheduled_at.replace(tzinfo=None) if scheduled_at.tzinfo else scheduled_at
                should_start_now = scheduled_naive <= datetime.utcnow()
            if should_start_now:
                payload["started_at"] = datetime.utcnow()

        new_check = await check_instance.create(db, obj_in=payload)
        
        # Send webhook event (fire and forget)
        try:
            await webhook_service.send_check_created({
                "check_id": str(new_check.id),
                "template_id": str(check_data.template_id),
                "inspector_id": str(payload["inspector_id"]),
                "brigade_id": str(new_check.brigade_id) if new_check.brigade_id else None,
            })
        except Exception:
            pass  # Don't fail request if webhook fails
        
        return new_check
    except NotFoundError:
        raise
    except ValidationError:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании чек-листа: {str(e)}"
        )


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

    if check_obj.brigade_id and check_obj.finished_at:
        score_value = checklist_service.calculate_score(template_obj.schema, check_obj.answers)
        await brigade_score.upsert_score(
            db,
            brigade_id=check_obj.brigade_id,
            score_date=check_obj.finished_at.date(),
            score=score_value,
            check_id=check_id,
            details={
                "check_id": str(check_id),
                "score": score_value,
                "finished_at": check_obj.finished_at.isoformat(),
            },
        )

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

