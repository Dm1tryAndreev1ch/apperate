"""Checklist schemas."""
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from app.models.checklist import TemplateStatus, CheckStatus


class ChecklistTemplateBase(BaseModel):
    """Base checklist template schema."""

    name: str
    description: Optional[str] = None
    schema: Dict[str, Any]  # JSONB structure


class ChecklistTemplateCreate(ChecklistTemplateBase):
    """Checklist template creation schema."""

    pass


class ChecklistTemplateUpdate(BaseModel):
    """Checklist template update schema."""

    name: Optional[str] = None
    description: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None
    status: Optional[TemplateStatus] = None


class ChecklistTemplateResponse(ChecklistTemplateBase):
    """Checklist template response schema."""

    id: UUID
    version: int
    status: TemplateStatus
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChecklistTemplateVersionResponse(BaseModel):
    """Checklist template version response schema."""

    id: UUID
    template_id: UUID
    version: int
    schema: Dict[str, Any]
    diff: Optional[Dict[str, Any]] = None
    created_by: Optional[UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True


class CheckInstanceBase(BaseModel):
    """Base check instance schema."""

    template_id: UUID
    project_id: Optional[str] = None
    department_id: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    inspector_id: Optional[UUID] = None
    brigade_id: Optional[UUID] = None


class CheckInstanceCreate(CheckInstanceBase):
    """Check instance creation schema."""

    pass


class CheckInstanceUpdate(BaseModel):
    """Check instance update schema."""

    answers: Optional[Dict[str, Any]] = None
    comments: Optional[Dict[str, Any]] = None
    media_keys: Optional[List[str]] = None
    status: Optional[CheckStatus] = None
    started_at: Optional[datetime] = None


class CheckInstanceResponse(CheckInstanceBase):
    """Check instance response schema."""

    id: UUID
    template_version: int
    status: CheckStatus
    answers: Dict[str, Any]
    comments: Optional[Dict[str, Any]] = None
    media_keys: Optional[List[str]] = None
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

