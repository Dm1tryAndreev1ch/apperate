"""Report schemas."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.report import ReportFormatXLSX, ReportStatus


class ReportBase(BaseModel):
    """Base report schema."""

    check_instance_id: UUID
    format: ReportFormatXLSX


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
    author_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

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
    """Payload for triggering Excel export. All fields are optional with sensible defaults."""

    year: Optional[int] = Field(default=None, description="Year (default: current year)")
    month: Optional[int] = Field(default=None, ge=1, le=12, description="Month 1-12 (default: current month)")
    brigade_ids: Optional[List[UUID]] = Field(default=None, description="List of brigade UUIDs to include (default: all)")
    expires_in: Optional[int] = Field(default=3600, ge=60, le=24 * 3600, description="Download URL expiration in seconds")


class MonthlyCultureReportResponse(BaseModel):
    """Excel report metadata."""

    file_key: str
    download_url: str
    filename: str
    month: date


class BulkGenerateReportsRequest(BaseModel):
    """Request for bulk report generation."""

    check_instance_ids: List[UUID] = Field(..., description="List of check instance IDs to generate reports for")
    trigger_bitrix: bool = Field(default=False, description="Trigger Bitrix ticket creation for alerts")


class BulkGenerateReportsResponse(BaseModel):
    """Response for bulk report generation."""

    success_count: int
    failed_count: int
    reports: List[ReportResponse]
    errors: List[Dict[str, str]] = Field(default_factory=list)


class BulkDeleteReportsRequest(BaseModel):
    """Request for bulk report deletion."""

    report_ids: List[UUID] = Field(..., description="List of report IDs to delete")

