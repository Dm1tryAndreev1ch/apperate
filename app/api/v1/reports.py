"""Reports API endpoints."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import Permission
from app.crud.report import report
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.checklist import CheckInstance, CheckStatus
from app.models.report import Report, ReportStatus
from app.models.user import User
from app.schemas.report import (
    ReportAnalyticsResponse,
    ReportDownloadResponse,
    ReportResponse,
    TimeSeriesPoint,
)
from app.services.storage_service import storage_service

router = APIRouter()


@router.get("", response_model=List[ReportResponse])
async def list_reports(
    skip: int = 0,
    limit: int = 100,
    check_instance_id: Optional[UUID] = None,
    status_filter: Optional[ReportStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List reports with filters."""
    filters = {}
    if check_instance_id:
        filters["check_instance_id"] = check_instance_id
    if status_filter:
        filters["status"] = status_filter

    reports = await report.get_multi(db, skip=skip, limit=limit, filters=filters)
    return reports


@router.get("/analytics", response_model=ReportAnalyticsResponse)
async def report_analytics(
    days: int = 14,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_VIEW)),
):
    """Return aggregated analytics for dashboards."""
    days = max(1, min(days, 90))
    to_date = datetime.utcnow().date()
    from_date = to_date - timedelta(days=days - 1)

    # Reports by status
    status_rows = await db.execute(
        select(Report.status, func.count(Report.id)).group_by(Report.status)
    )
    by_status: Dict[str, int] = {
        row[0].value if isinstance(row[0], ReportStatus) else str(row[0]): row[1]
        for row in status_rows
    }

    # Reports by format
    format_rows = await db.execute(
        select(Report.format, func.count(Report.id)).group_by(Report.format)
    )
    by_format: Dict[str, int] = {
        str(row[0]): row[1] for row in format_rows
    }

    # Completed checks per day
    checks_rows = await db.execute(
        select(
            func.date(CheckInstance.finished_at).label("day"),
            func.count(CheckInstance.id),
        )
        .where(
            CheckInstance.finished_at.is_not(None),
            CheckInstance.finished_at >= from_date,
            CheckInstance.status == CheckStatus.COMPLETED,
        )
        .group_by("day")
        .order_by("day")
    )
    checks_map = {row[0]: row[1] for row in checks_rows}
    checks_completed = [
        TimeSeriesPoint(label=day.isoformat(), value=float(checks_map.get(day, 0)))
        for day in (from_date + timedelta(days=i) for i in range(days))
    ]

    # Average brigade score over window
    brigade_rows = await db.execute(
        select(
            Brigade.name,
            func.coalesce(func.avg(BrigadeDailyScore.score), 0).label("avg_score"),
        )
        .select_from(Brigade)
        .join(BrigadeDailyScore, BrigadeDailyScore.brigade_id == Brigade.id, isouter=True)
        .where(
            Brigade.is_active.is_(True),
            func.coalesce(BrigadeDailyScore.score_date, to_date) >= from_date,
        )
        .group_by(Brigade.id)
        .order_by(func.coalesce(func.avg(BrigadeDailyScore.score), 0).desc())
    )
    brigade_scores = [
        TimeSeriesPoint(label=row[0], value=float(row[1] or 0)) for row in brigade_rows
    ]

    return ReportAnalyticsResponse(
        by_status=by_status,
        by_format=by_format,
        checks_completed=checks_completed,
        brigade_scores=brigade_scores,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a report by ID."""
    report_obj = await report.get(db, id=report_id)
    if not report_obj:
        raise NotFoundError("Report not found")
    return report_obj


@router.get("/{report_id}/download", response_model=ReportDownloadResponse)
async def download_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_DOWNLOAD)),
):
    """Get presigned URL for downloading a report."""
    report_obj = await report.get(db, id=report_id)
    if not report_obj:
        raise NotFoundError("Report not found")

    if report_obj.status != ReportStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is not ready. Status: {report_obj.status}",
        )

    if not report_obj.file_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found")

    download_url = storage_service.generate_download_url(report_obj.file_key, expires_in=3600)
    return ReportDownloadResponse(download_url=download_url, expires_in=3600)

