"""Schedule schemas."""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, root_validator
from datetime import datetime


class ScheduleBase(BaseModel):
    """Base schedule schema."""

    name: str
    template_id: Optional[UUID] = None
    cron_or_rrule: str
    assigned_user_ids: Optional[List[UUID]] = None  # Backwards compatibility
    inspector_pool: Optional[List[UUID]] = None
    brigade_pool: Optional[List[UUID]] = None
    auto_replace_on_absence: bool = False
    timezone: str = "UTC"
    enabled: bool = True


class ScheduleCreate(ScheduleBase):
    """Schedule creation schema."""

    @root_validator(pre=True)
    def _sync_deprecated_fields(cls, values):
        inspector_pool = values.get("inspector_pool")
        assigned = values.get("assigned_user_ids")
        if inspector_pool is None and assigned is not None:
            values["inspector_pool"] = assigned
        return values


class ScheduleUpdate(BaseModel):
    """Schedule update schema."""

    name: Optional[str] = None
    template_id: Optional[UUID] = None
    cron_or_rrule: Optional[str] = None
    assigned_user_ids: Optional[List[UUID]] = None
    inspector_pool: Optional[List[UUID]] = None
    brigade_pool: Optional[List[UUID]] = None
    auto_replace_on_absence: Optional[bool] = None
    timezone: Optional[str] = None
    enabled: Optional[bool] = None

    @root_validator(pre=True)
    def _sync_update_fields(cls, values):
        inspector_pool = values.get("inspector_pool")
        assigned = values.get("assigned_user_ids")
        if inspector_pool is None and assigned is not None:
            values["inspector_pool"] = assigned
        return values


class ScheduleResponse(ScheduleBase):
    """Schedule response schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    last_inspector_index: int
    last_brigade_index: int

    class Config:
        from_attributes = True


class ScheduleTriggerRequest(BaseModel):
    """Payload for manual schedule triggering."""

    inspector_id: Optional[UUID] = None
    brigade_id: Optional[UUID] = None

