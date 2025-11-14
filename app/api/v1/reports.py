"""Reports API endpoints."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from io import BytesIO
from typing import Dict, Iterator, List, Optional
from uuid import UUID

import asyncio
import base64

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.security import Permission
from app.crud.report import report
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.checklist import CheckInstance, CheckStatus
from app.models.report import Report, ReportStatus, ReportFormatXLSX
from app.models.reporting import PeriodSummaryGranularity, ReportPeriodSummary
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
from app.services.analytics_service import AnalyticsService, PeriodSummaryDTO
from app.services.excel_export_service import generate_monthly_culture_report
from app.services.report_builder import report_builder
from app.services.report_dispatcher import report_dispatcher
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


@router.post("/generate/{check_instance_id}", response_model=ReportResponse)
async def generate_report(
    check_instance_id: UUID,
    trigger_bitrix: bool = Query(default=True, description="Trigger Bitrix ticket creation for alerts"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_GENERATE)),
):
    """Generate a new Excel report for a check instance."""
    # Load check instance
    result = await db.execute(
        select(CheckInstance)
        .where(CheckInstance.id == check_instance_id)
        .options(selectinload(CheckInstance.template), selectinload(CheckInstance.inspector), selectinload(CheckInstance.brigade))
    )
    check_instance = result.scalar_one_or_none()
    if not check_instance:
        raise NotFoundError("Check instance not found")

    if check_instance.status != CheckStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only generate reports for completed checks",
        )

    # Generate report using dispatcher
    report_obj = await report_dispatcher.generate_and_dispatch_report(
        db,
        check_instance=check_instance,
        author=current_user,
        trigger_bitrix=trigger_bitrix,
    )

    return report_obj


@router.get("", response_model=List[ReportResponse])
async def list_reports(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    check_instance_id: Optional[UUID] = None,
    status_filter: Optional[ReportStatus] = None,
    author_id: Optional[UUID] = None,
    sort_by: str = Query(default="created_at", description="Sort field: created_at, author, status"),
    sort_order: str = Query(default="desc", description="Sort order: asc or desc"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List reports with filters and sorting."""
    # Build base query
    query = select(Report).options(selectinload(Report.author), selectinload(Report.check_instance))

    # Apply filters
    filters = []
    if check_instance_id:
        filters.append(Report.check_instance_id == check_instance_id)
    if status_filter:
        filters.append(Report.status == status_filter)
    if author_id:
        filters.append(Report.author_id == author_id)
    if date_from:
        filters.append(Report.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        filters.append(Report.created_at <= datetime.combine(date_to, datetime.max.time()))

    if filters:
        query = query.where(*filters)

    # Apply sorting
    sort_field_map = {
        "created_at": Report.created_at,
        "author": Report.author_id,  # Sort by author ID (can be enhanced to sort by name)
        "status": Report.status,
    }
    sort_field = sort_field_map.get(sort_by, Report.created_at)
    if sort_order.lower() == "asc":
        query = query.order_by(asc(sort_field))
    else:
        query = query.order_by(desc(sort_field))

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    reports = result.scalars().all()

    return reports


@router.get("/analytics", response_model=ReportAnalyticsResponse)
async def report_analytics(
    days: int = Query(default=14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_VIEW)),
):
    """Return aggregated analytics for dashboards."""
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

    # Reports by format (now only XLSX)
    by_format: Dict[str, int] = {"xlsx": 0}
    format_rows = await db.execute(
        select(Report.format, func.count(Report.id)).group_by(Report.format)
    )
    for row in format_rows:
        by_format[str(row[0])] = row[1]

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


@router.get("/summaries", response_model=List[Dict])
async def list_period_summaries(
    granularity: PeriodSummaryGranularity = Query(default=PeriodSummaryGranularity.MONTH),
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    department_id: Optional[str] = None,
    brigade_id: Optional[UUID] = None,
    author_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_VIEW)),
):
    """List period summaries with optional filters."""
    # Default to current period if not specified
    today = datetime.utcnow().date()
    if not period_start:
        if granularity == PeriodSummaryGranularity.DAY:
            period_start = today
        elif granularity == PeriodSummaryGranularity.WEEK:
            # Start of current week (Monday)
            days_since_monday = today.weekday()
            period_start = today - timedelta(days=days_since_monday)
        else:  # MONTH
            period_start = today.replace(day=1)

    if not period_end:
        if granularity == PeriodSummaryGranularity.DAY:
            period_end = period_start
        elif granularity == PeriodSummaryGranularity.WEEK:
            period_end = period_start + timedelta(days=6)
        else:  # MONTH
            from calendar import monthrange
            _, days_in_month = monthrange(period_start.year, period_start.month)
            period_end = period_start.replace(day=days_in_month)

    # Compute summary using analytics service
    summary = await AnalyticsService.compute_period_summary(
        db,
        granularity=granularity.value,
        period_start=period_start,
        period_end=period_end,
        department_id=department_id,
        brigade_id=brigade_id,
        author_id=author_id,
    )

    return [
        {
            "granularity": summary.granularity,
            "period_start": summary.period_start.isoformat(),
            "period_end": summary.period_end.isoformat(),
            "report_count": summary.report_count,
            "avg_score": float(summary.avg_score) if summary.avg_score else None,
            "remark_count": summary.remark_count,
            "delta_metrics": {k: float(v) for k, v in summary.delta_metrics.items()},
            "brigade_scores": [
                {
                    "brigade_id": str(bs.brigade_id),
                    "brigade_name": bs.brigade_name,
                    "score_date": bs.score_date.isoformat(),
                    "score": float(bs.score),
                    "overall_score": float(bs.overall_score) if bs.overall_score else None,
                }
                for bs in summary.brigade_scores
            ],
        }
    ]


@router.post("/summaries/export")
async def export_period_summary(
    granularity: PeriodSummaryGranularity = Body(default=PeriodSummaryGranularity.MONTH),
    period_start: date = Body(...),
    period_end: date = Body(...),
    department_id: Optional[str] = Body(default=None),
    brigade_id: Optional[UUID] = Body(default=None),
    author_id: Optional[UUID] = Body(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_EXPORT)),
):
    """Export period summary as Excel file."""
    # Compute summary
    summary = await AnalyticsService.compute_period_summary(
        db,
        granularity=granularity.value,
        period_start=period_start,
        period_end=period_end,
        department_id=department_id,
        brigade_id=brigade_id,
        author_id=author_id,
    )

    # Build Excel workbook
    workbook_bytes = report_builder.build_period_summary_workbook(summary=summary)

    # Upload to storage
    file_key = f"reports/summaries/{granularity.value}/{period_start.isoformat}_{period_end.isoformat}.xlsx"
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    storage_service.upload_fileobj(
        BytesIO(workbook_bytes),
        file_key,
        content_type=content_type,
    )

    # Generate download URL
    download_url = storage_service.generate_download_url(file_key, expires_in=3600)

    return {
        "file_key": file_key,
        "download_url": download_url,
        "filename": f"summary-{granularity.value}-{period_start.isoformat()}.xlsx",
    }


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a report by ID."""
    result = await db.execute(
        select(Report)
        .where(Report.id == report_id)
        .options(selectinload(Report.author), selectinload(Report.check_instance))
    )
    report_obj = result.scalar_one_or_none()
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

    # Generate presigned URL from storage service
    download_url = storage_service.generate_download_url(report_obj.file_key, expires_in=3600)
    return ReportDownloadResponse(download_url=download_url, expires_in=3600)


@router.get("/{report_id}/file", name="download_report_file")
async def download_report_file(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_DOWNLOAD)),
):
    """Stream report file through the API (Excel-only)."""
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

    # Ensure format is XLSX
    if report_obj.format != ReportFormatXLSX.XLSX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only Excel (XLSX) reports are supported",
        )

    try:
        s3_object = await asyncio.to_thread(storage_service.get_object, report_obj.file_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report file unavailable: {exc}",
        ) from exc

    body = s3_object["Body"]
    content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    filename = f"mantaqc-report-{report_obj.id}.xlsx"

    def file_iterator(streaming_body) -> Iterator[bytes]:
        try:
            for chunk in streaming_body.iter_chunks(chunk_size=1024 * 512):
                if chunk:
                    yield chunk
        finally:
            streaming_body.close()

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Content-Type": content_type,
    }

    return StreamingResponse(file_iterator(body), media_type=content_type, headers=headers)


@router.get("/checks/{check_id}/logs")
async def get_check_logs(
    check_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get check instance logs in HTML-safe JSON format for web viewing."""
    result = await db.execute(
        select(CheckInstance)
        .where(CheckInstance.id == check_id)
        .options(selectinload(CheckInstance.template), selectinload(CheckInstance.inspector), selectinload(CheckInstance.brigade))
    )
    check_instance = result.scalar_one_or_none()
    if not check_instance:
        raise NotFoundError("Check instance not found")

    # Build log structure
    template_schema = check_instance.template.schema if check_instance.template else {}
    answers = check_instance.answers or {}
    comments = check_instance.comments or {}
    media_keys = check_instance.media_keys or []

    log_sections = []
    for section in template_schema.get("sections", []):
        section_name = section.get("title") or section.get("name", "Без названия")
        section_items = []

        for question in section.get("questions", []):
            question_id = question.get("id")
            question_text = question.get("text") or question_id
            answer = answers.get(question_id)
            comment = comments.get(question_id) or comments.get("summary")
            has_media = any(str(k) == str(question_id) for k in media_keys)

            section_items.append({
                "question_id": question_id,
                "question_text": question_text,
                "answer": answer,
                "comment": comment,
                "has_media": has_media,
                "question_type": question.get("type"),
            })

        log_sections.append({
            "section_name": section_name,
            "items": section_items,
        })

    return {
        "check_id": str(check_instance.id),
        "template_name": check_instance.template.name if check_instance.template else "Unknown",
        "inspector": check_instance.inspector.full_name if check_instance.inspector else "Unknown",
        "status": check_instance.status.value if hasattr(check_instance.status, "value") else str(check_instance.status),
        "started_at": check_instance.started_at.isoformat() if check_instance.started_at else None,
        "finished_at": check_instance.finished_at.isoformat() if check_instance.finished_at else None,
        "project_id": check_instance.project_id,
        "department_id": check_instance.department_id,
        "brigade_name": check_instance.brigade.name if check_instance.brigade else None,
        "sections": log_sections,
        "audit_trail": check_instance.audit or {},
    }
