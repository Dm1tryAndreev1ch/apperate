"""Schedule schemas."""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class ScheduleBase(BaseModel):
    """Base schedule schema."""

    name: str
    template_id: Optional[UUID] = None
    cron_or_rrule: str
    assigned_user_ids: Optional[List[UUID]] = None
    auto_replace_on_absence: bool = False
    timezone: str = "UTC"
    enabled: bool = True


class ScheduleCreate(ScheduleBase):
    """Schedule creation schema."""

    pass


class ScheduleUpdate(BaseModel):
    """Schedule update schema."""

    name: Optional[str] = None
    template_id: Optional[UUID] = None
    cron_or_rrule: Optional[str] = None
    assigned_user_ids: Optional[List[UUID]] = None
    auto_replace_on_absence: Optional[bool] = None
    timezone: Optional[str] = None
    enabled: Optional[bool] = None


class ScheduleResponse(ScheduleBase):
    """Schedule response schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

