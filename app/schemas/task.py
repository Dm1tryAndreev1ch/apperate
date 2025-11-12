"""Task schemas."""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class TaskLocalBase(BaseModel):
    """Base task schema."""

    title: str
    description: Optional[str] = None
    status: str = "PENDING"


class TaskLocalCreate(TaskLocalBase):
    """Task creation schema."""

    report_id: Optional[UUID] = None


class TaskLocalResponse(TaskLocalBase):
    """Task response schema."""

    id: UUID
    report_id: Optional[UUID] = None
    bitrix_id: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

