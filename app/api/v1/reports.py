"""Reports API endpoints."""
from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Dict, Iterator, List, Optional
from uuid import UUID

import asyncio
import base64

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
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
    ChartImage,
    MonthlyCultureReportRequest,
    MonthlyCultureReportResponse,
    ReportAnalyticsResponse,
    ReportDownloadResponse,
    ReportResponse,
    TimeSeriesPoint,
)
from app.services.excel_export_service import generate_monthly_culture_report
from app.services.storage_service import storage_service

router = APIRouter()


def _figure_to_data_uri(fig) -> str:
    """Convert a matplotlib figure to a PNG data URI."""
    buffer = BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode("ascii")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


def _create_pie_chart(data: Dict[str, int], title: str) -> Optional[str]:
    """Render a pie chart from dictionary data."""
    if not data:
        return None

    labels = list(data.keys())
    values = list(data.values())
    total = sum(values)
    if total == 0:
        return None

    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    ax.pie(
        values,
        labels=labels,
        autopct=lambda pct: f"{pct:.0f}%\n({int(round(pct * total / 100))})" if pct > 0 else "",
        startangle=90,
    )
    ax.set_title(title)
    return _figure_to_data_uri(fig)


def _create_line_chart(points: List[TimeSeriesPoint], title: str, ylabel: str) -> Optional[str]:
    """Render a line chart from a sequence of time series points."""
    if not points:
        return None

    labels = [point.label for point in points]
    values = [point.value for point in points]
    if not any(values):
        return None

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(labels, values, marker="o", linewidth=2)
    ax.set_title(title)
    ax.set_xlabel("Дата")
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return _figure_to_data_uri(fig)


def _create_bar_chart(points: List[TimeSeriesPoint], title: str, ylabel: str) -> Optional[str]:
    """Render a bar chart from a sequence of time series points."""
    if not points:
        return None

    labels = [point.label for point in points]
    values = [point.value for point in points]
    if not any(values):
        return None

    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.bar(labels, values, color="#4a90e2")
    ax.set_title(title)
    ax.set_xlabel("Бригада")
    ax.set_ylabel(ylabel)
    ax.set_ylim(0, max(values) * 1.1 if values else 1)
    ax.grid(axis="y", linestyle="--", alpha=0.3)
    ax.tick_params(axis="x", rotation=20)
    fig.tight_layout()
    return _figure_to_data_uri(fig)


@router.post(
    "/excel/monthly-culture",
    response_model=MonthlyCultureReportResponse,
    summary="Generate monthly culture Excel report",
)
async def create_monthly_culture_report(
    payload: MonthlyCultureReportRequest = Body(default_factory=MonthlyCultureReportRequest),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_permission(Permission.REPORT_EXPORT)),
):
    """Generate Excel report aggregating brigade culture metrics."""
    today = datetime.utcnow().date()
    year = payload.year or today.year
    month_number = payload.month or today.month

    try:
        month_date = date(year, month_number, 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректные значения года или месяца.",
        ) from exc

    result = await generate_monthly_culture_report(
        db,
        month=month_date,
        brigade_ids=payload.brigade_ids,
        expires_in=payload.expires_in,
    )
    return {
        **result,
        "month": month_date,
    }


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

    charts: Dict[str, ChartImage] = {}

    status_chart_uri = _create_pie_chart(
        by_status, "Распределение отчётов по статусам"
    )
    if status_chart_uri:
        charts["by_status"] = ChartImage(
            title="Распределение отчётов по статусам",
            kind="pie",
            image=status_chart_uri,
        )

    format_chart_uri = _create_pie_chart(
        by_format, "Распределение отчётов по форматам"
    )
    if format_chart_uri:
        charts["by_format"] = ChartImage(
            title="Распределение отчётов по форматам",
            kind="pie",
            image=format_chart_uri,
        )

    checks_chart_uri = _create_line_chart(
        checks_completed, "Завершённые проверки по дням", "Количество проверок"
    )
    if checks_chart_uri:
        charts["checks_completed"] = ChartImage(
            title="Завершённые проверки по дням",
            kind="line",
            image=checks_chart_uri,
        )

    brigade_chart_uri = _create_bar_chart(
        brigade_scores, "Средний балл активных бригад", "Средний балл"
    )
    if brigade_chart_uri:
        charts["brigade_scores"] = ChartImage(
            title="Средний балл активных бригад",
            kind="bar",
            image=brigade_chart_uri,
        )

    return ReportAnalyticsResponse(
        by_status=by_status,
        by_format=by_format,
        checks_completed=checks_completed,
        brigade_scores=brigade_scores,
        charts=charts,
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
    request: Request,
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

    download_url = request.url_for("download_report_file", report_id=str(report_id))
    return ReportDownloadResponse(download_url=str(download_url), expires_in=3600)


@router.get("/{report_id}/file", name="download_report_file")
async def download_report_file(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_DOWNLOAD)),
):
    """Stream report file through the API so the browser does not hit MinIO directly."""
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

    try:
        s3_object = await asyncio.to_thread(storage_service.get_object, report_obj.file_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report file unavailable: {exc}",
        ) from exc

    body = s3_object["Body"]
    content_type = s3_object.get("ContentType") or "application/octet-stream"
    filename = f"report-{report_obj.id}.{report_obj.format.value}" if report_obj.format else f"{report_obj.id}"

    def file_iterator(streaming_body) -> Iterator[bytes]:
        try:
            for chunk in streaming_body.iter_chunks(chunk_size=1024 * 512):
                if chunk:
                    yield chunk
        finally:
            streaming_body.close()

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }

    return StreamingResponse(file_iterator(body), media_type=content_type, headers=headers)

