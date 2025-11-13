"""Advanced scheduling utilities."""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.crud.checklist import check_instance, template
from app.models.checklist import CheckInstance, CheckStatus
from app.models.schedule import Schedule


def _ensure_uuid(value: Optional[UUID]) -> Optional[UUID]:
    """Normalize UUID values that may be returned as strings by SQLite."""
    if value is None or isinstance(value, UUID):
        return value
    return UUID(str(value))


class ScheduleService:
    """Helper routines for rotating inspector/brigade assignments."""

    @staticmethod
    def _pick_next(pool: Optional[Sequence[UUID]], last_index: int) -> Tuple[Optional[UUID], int]:
        if not pool:
            return None, last_index
        pool = list(pool)
        next_index = last_index % len(pool)
        chosen = pool[next_index]
        next_pointer = (next_index + 1) % len(pool)
        return chosen, next_pointer

    async def spawn_check(
        self,
        db: AsyncSession,
        schedule_obj: Schedule,
        *,
        force_brigade_id: Optional[UUID] = None,
        force_inspector_id: Optional[UUID] = None,
    ) -> CheckInstance:
        """Create a new check instance based on schedule rotation."""
        if not schedule_obj.template_id:
            raise NotFoundError("Schedule is missing template assignment")

        template_obj = await template.get(db, id=schedule_obj.template_id)
        if not template_obj:
            raise NotFoundError("Template referenced by schedule not found")

        inspector_id = force_inspector_id
        if inspector_id is None:
            inspector_id, next_index = self._pick_next(
                schedule_obj.inspector_pool or schedule_obj.assigned_user_ids,
                schedule_obj.last_inspector_index,
            )
            schedule_obj.last_inspector_index = next_index

        brigade_id = force_brigade_id
        if brigade_id is None:
            brigade_id, next_brigade_idx = self._pick_next(
                schedule_obj.brigade_pool,
                schedule_obj.last_brigade_index,
            )
            schedule_obj.last_brigade_index = next_brigade_idx

        inspector_id = _ensure_uuid(inspector_id)
        brigade_id = _ensure_uuid(brigade_id)

        payload = {
            "template_id": template_obj.id,
            "template_version": template_obj.version,
            "scheduled_at": datetime.utcnow(),
            "inspector_id": inspector_id,
            "brigade_id": brigade_id,
            "status": CheckStatus.IN_PROGRESS,
            "started_at": datetime.utcnow(),
        }
        # Remove None keys
        payload = {k: v for k, v in payload.items() if v is not None}

        new_check = await check_instance.create(db, obj_in=payload)
        db.add(schedule_obj)
        await db.commit()
        await db.refresh(new_check)
        await db.refresh(schedule_obj)
        return new_check


schedule_service = ScheduleService()


