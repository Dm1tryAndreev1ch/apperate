"""Report schemas."""
from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

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


class TimeSeriesPoint(BaseModel):
    """Generic time series point."""

    label: str
    value: float


class ChartImage(BaseModel):
    """Rendered chart in base64 encoding."""

    title: str
    kind: str
    image: str


class ReportAnalyticsResponse(BaseModel):
    """Aggregated analytics for dashboards."""

    by_status: Dict[str, int]
    by_format: Dict[str, int]
    checks_completed: List[TimeSeriesPoint]
    brigade_scores: List[TimeSeriesPoint]
    charts: Dict[str, ChartImage] = Field(default_factory=dict)


class MonthlyCultureReportRequest(BaseModel):
    """Payload for triggering Excel export."""

    year: Optional[int] = None
    month: Optional[int] = None
    brigade_ids: Optional[List[UUID]] = None
    expires_in: int = Field(default=3600, ge=60, le=24 * 3600)


class MonthlyCultureReportResponse(BaseModel):
    """Excel report metadata."""

    file_key: str
    download_url: str
    filename: str
    month: date

