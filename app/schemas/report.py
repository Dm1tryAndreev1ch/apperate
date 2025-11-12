"""Report schemas."""
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
from app.models.report import ReportFormat, ReportStatus


class ReportBase(BaseModel):
    """Base report schema."""

    check_instance_id: UUID
    format: ReportFormat


class ReportCreate(ReportBase):
    """Report creation schema."""

    pass


class ReportResponse(ReportBase):
    """Report response schema."""

    id: UUID
    file_key: Optional[str] = None
    status: ReportStatus
    created_at: datetime
    generated_by: Optional[UUID] = None

    class Config:
        from_attributes = True


class ReportDownloadResponse(BaseModel):
    """Report download response schema."""

    download_url: str
    expires_in: int

