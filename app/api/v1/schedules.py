"""Schedules API endpoints (Admin)."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import Permission
from app.crud.schedule import schedule
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import User
from app.schemas.checklist import CheckInstanceResponse
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleResponse,
    ScheduleTriggerRequest,
    ScheduleUpdate,
)
from app.services.schedule_service import schedule_service

router = APIRouter()


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SCHEDULE_VIEW)),
):
    """List all schedules."""
    schedules = await schedule.get_multi(db, skip=skip, limit=limit)
    return schedules


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SCHEDULE_CREATE)),
):
    """Create a new schedule."""
    new_schedule = await schedule.create(db, obj_in=schedule_data)
    return new_schedule


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SCHEDULE_VIEW)),
):
    """Get a schedule by ID."""
    schedule_obj = await schedule.get(db, id=schedule_id)
    if not schedule_obj:
        raise NotFoundError("Schedule not found")
    return schedule_obj


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    schedule_data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SCHEDULE_UPDATE)),
):
    """Update a schedule."""
    schedule_obj = await schedule.get(db, id=schedule_id)
    if not schedule_obj:
        raise NotFoundError("Schedule not found")
    updated_schedule = await schedule.update(db, db_obj=schedule_obj, obj_in=schedule_data)
    return updated_schedule


@router.post("/{schedule_id}/trigger", response_model=CheckInstanceResponse, status_code=status.HTTP_201_CREATED)
async def trigger_schedule(
    schedule_id: UUID,
    payload: ScheduleTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SCHEDULE_CREATE)),
):
    """Manually trigger schedule to create a check instance."""
    schedule_obj = await schedule.get(db, id=schedule_id)
    if not schedule_obj:
        raise NotFoundError("Schedule not found")

    new_check = await schedule_service.spawn_check(
        db,
        schedule_obj,
        force_brigade_id=payload.brigade_id,
        force_inspector_id=payload.inspector_id,
    )
    return new_check


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.SCHEDULE_DELETE)),
):
    """Delete a schedule."""
    schedule_obj = await schedule.get(db, id=schedule_id)
    if not schedule_obj:
        raise NotFoundError("Schedule not found")
    await schedule.remove(db, id=schedule_id)

