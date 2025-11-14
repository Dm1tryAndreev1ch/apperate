"""Dashboard API endpoints for admin and user dashboards."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import Permission
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.checklist import CheckInstance, CheckStatus
from app.models.report import Report, ReportStatus
from app.models.reporting import RemarkEntry, RemarkSeverity
from app.models.user import User
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/admin")
async def admin_dashboard(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_VIEW)),
):
    """Admin dashboard with global KPIs and metrics."""
    to_date = datetime.utcnow().date()
    from_date = to_date - timedelta(days=days - 1)

    # Total reports
    total_reports_result = await db.execute(
        select(func.count(Report.id)).where(Report.status == ReportStatus.READY)
    )
    total_reports = total_reports_result.scalar_one_or_none() or 0

    # Recent reports (last 10)
    recent_reports_result = await db.execute(
        select(Report)
        .where(Report.status == ReportStatus.READY)
        .options(selectinload(Report.author), selectinload(Report.check_instance))
        .order_by(Report.created_at.desc())
        .limit(10)
    )
    recent_reports = recent_reports_result.scalars().all()

    # Reports by status
    status_result = await db.execute(
        select(Report.status, func.count(Report.id)).group_by(Report.status)
    )
    reports_by_status = {
        row[0].value if hasattr(row[0], "value") else str(row[0]): row[1]
        for row in status_result
    }

    # Completed checks in period
    completed_checks_result = await db.execute(
        select(func.count(CheckInstance.id)).where(
            CheckInstance.status == CheckStatus.COMPLETED,
            CheckInstance.finished_at.isnot(None),
            CheckInstance.finished_at >= datetime.combine(from_date, datetime.min.time()),
            CheckInstance.finished_at <= datetime.combine(to_date, datetime.max.time()),
        )
    )
    completed_checks = completed_checks_result.scalar_one_or_none() or 0

    # Active brigades count
    active_brigades_result = await db.execute(
        select(func.count(Brigade.id)).where(Brigade.is_active.is_(True))
    )
    active_brigades = active_brigades_result.scalar_one_or_none() or 0

    # Brigade scores (top 5)
    brigade_scores_result = await db.execute(
        select(
            Brigade.id,
            Brigade.name,
            func.avg(BrigadeDailyScore.score).label("avg_score"),
        )
        .select_from(Brigade)
        .join(BrigadeDailyScore, BrigadeDailyScore.brigade_id == Brigade.id, isouter=True)
        .where(
            Brigade.is_active.is_(True),
            func.coalesce(BrigadeDailyScore.score_date, to_date) >= from_date,
        )
        .group_by(Brigade.id, Brigade.name)
        .order_by(func.avg(BrigadeDailyScore.score).desc().nulls_last())
        .limit(5)
    )
    top_brigades = [
        {
            "brigade_id": str(row[0]),
            "brigade_name": row[1],
            "avg_score": float(row[2]) if row[2] else 0.0,
        }
        for row in brigade_scores_result
    ]

    # Critical remarks count
    critical_remarks_result = await db.execute(
        select(func.count(RemarkEntry.id)).where(
            RemarkEntry.severity == RemarkSeverity.CRITICAL,
            RemarkEntry.raised_at >= datetime.combine(from_date, datetime.min.time()),
        )
    )
    critical_remarks = critical_remarks_result.scalar_one_or_none() or 0

    # Outstanding Bitrix tasks (from report metadata)
    # Count reports that have Bitrix tickets created
    all_reports_result = await db.execute(
        select(Report.metadata_json).where(Report.status == ReportStatus.READY)
    )
    outstanding_bitrix_tasks = 0
    for row in all_reports_result:
        metadata = row[0] if row[0] else {}
        bitrix_data = metadata.get("bitrix", {})
        if bitrix_data.get("tickets_created", 0) > 0:
            outstanding_bitrix_tasks += 1

    # Recent reports summary
    recent_reports_summary = [
        {
            "id": str(r.id),
            "check_instance_id": str(r.check_instance_id),
            "created_at": r.created_at.isoformat(),
            "author": r.author.full_name if r.author else "Unknown",
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "avg_score": r.metadata_json.get("analytics", {}).get("avg_score"),
            "brigade_score": r.metadata_json.get("brigade_score", {}).get("score"),
        }
        for r in recent_reports
    ]

    return {
        "period": {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "days": days,
        },
        "kpis": {
            "total_reports": total_reports,
            "completed_checks": completed_checks,
            "active_brigades": active_brigades,
            "critical_remarks": critical_remarks,
            "outstanding_bitrix_tasks": outstanding_bitrix_tasks,
        },
        "reports_by_status": reports_by_status,
        "top_brigades": top_brigades,
        "recent_reports": recent_reports_summary,
    }


@router.get("/user")
async def user_dashboard(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """User dashboard showing only current user's data."""
    to_date = datetime.utcnow().date()
    from_date = to_date - timedelta(days=days - 1)

    # User's reports
    user_reports_result = await db.execute(
        select(func.count(Report.id)).where(
            Report.author_id == current_user.id,
            Report.status == ReportStatus.READY,
        )
    )
    user_reports_count = user_reports_result.scalar_one_or_none() or 0

    # User's recent reports
    recent_user_reports_result = await db.execute(
        select(Report)
        .where(
            Report.author_id == current_user.id,
            Report.status == ReportStatus.READY,
        )
        .options(selectinload(Report.check_instance))
        .order_by(Report.created_at.desc())
        .limit(10)
    )
    recent_user_reports = recent_user_reports_result.scalars().all()

    # User's completed checks
    user_checks_result = await db.execute(
        select(func.count(CheckInstance.id)).where(
            CheckInstance.inspector_id == current_user.id,
            CheckInstance.status == CheckStatus.COMPLETED,
            CheckInstance.finished_at.isnot(None),
            CheckInstance.finished_at >= datetime.combine(from_date, datetime.min.time()),
            CheckInstance.finished_at <= datetime.combine(to_date, datetime.max.time()),
        )
    )
    user_completed_checks = user_checks_result.scalar_one_or_none() or 0

    # User's average score from reports
    user_reports_for_avg_result = await db.execute(
        select(Report.metadata_json).where(
            Report.author_id == current_user.id,
            Report.status == ReportStatus.READY,
        )
    )
    scores = []
    for row in user_reports_for_avg_result:
        metadata = row[0] if row[0] else {}
        analytics = metadata.get("analytics", {})
        avg_score = analytics.get("avg_score")
        if avg_score is not None:
            try:
                scores.append(float(avg_score))
            except (ValueError, TypeError):
                pass
    user_avg_score_float = sum(scores) / len(scores) if scores else None

    # User's brigade scores (if user is in a brigade)
    user_brigade_scores: List[Dict] = []
    if current_user.brigades:
        brigade_ids = [brigade.id for brigade in current_user.brigades]
        brigade_scores_result = await db.execute(
            select(
                Brigade.id,
                Brigade.name,
                BrigadeDailyScore.score_date,
                BrigadeDailyScore.score,
                BrigadeDailyScore.overall_score,
            )
            .select_from(Brigade)
            .join(BrigadeDailyScore, BrigadeDailyScore.brigade_id == Brigade.id)
            .where(
                Brigade.id.in_(brigade_ids),
                BrigadeDailyScore.score_date >= from_date,
                BrigadeDailyScore.score_date <= to_date,
            )
            .order_by(BrigadeDailyScore.score_date.desc())
            .limit(10)
        )
        user_brigade_scores = [
            {
                "brigade_id": str(row[0]),
                "brigade_name": row[1],
                "score_date": row[2].isoformat(),
                "score": float(row[3]) if row[3] else 0.0,
                "overall_score": float(row[4]) if row[4] else None,
            }
            for row in brigade_scores_result
        ]

    # User's assigned checks (in progress)
    assigned_checks_result = await db.execute(
        select(CheckInstance)
        .where(
            CheckInstance.inspector_id == current_user.id,
            CheckInstance.status == CheckStatus.IN_PROGRESS,
        )
        .options(selectinload(CheckInstance.template))
        .order_by(CheckInstance.scheduled_at.desc().nulls_last())
        .limit(5)
    )
    assigned_checks = assigned_checks_result.scalars().all()

    # Recent reports summary
    recent_reports_summary = [
        {
            "id": str(r.id),
            "check_instance_id": str(r.check_instance_id),
            "created_at": r.created_at.isoformat(),
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "avg_score": r.metadata_json.get("analytics", {}).get("avg_score"),
            "brigade_score": r.metadata_json.get("brigade_score", {}).get("score"),
        }
        for r in recent_user_reports
    ]

    # Assigned checks summary
    assigned_checks_summary = [
        {
            "id": str(c.id),
            "template_name": c.template.name if c.template else "Unknown",
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "project_id": c.project_id,
            "department_id": c.department_id,
        }
        for c in assigned_checks
    ]

    return {
        "period": {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "days": days,
        },
        "kpis": {
            "total_reports": user_reports_count,
            "completed_checks": user_completed_checks,
            "avg_score": user_avg_score_float,
        },
        "recent_reports": recent_reports_summary,
        "brigade_scores": user_brigade_scores,
        "assigned_checks": assigned_checks_summary,
    }


@router.get("/brigade-scores")
async def brigade_scores_dashboard(
    days: int = Query(default=30, ge=1, le=365),
    brigade_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get brigade scores for dashboard visualization."""
    to_date = datetime.utcnow().date()
    from_date = to_date - timedelta(days=days - 1)

    # Build query
    query = (
        select(
            Brigade.id,
            Brigade.name,
            BrigadeDailyScore.score_date,
            BrigadeDailyScore.score,
            BrigadeDailyScore.overall_score,
            BrigadeDailyScore.formula_version,
        )
        .select_from(Brigade)
        .join(BrigadeDailyScore, BrigadeDailyScore.brigade_id == Brigade.id)
        .where(
            Brigade.is_active.is_(True),
            BrigadeDailyScore.score_date >= from_date,
            BrigadeDailyScore.score_date <= to_date,
        )
    )

    if brigade_id:
        query = query.where(Brigade.id == brigade_id)

    query = query.order_by(Brigade.name, BrigadeDailyScore.score_date.desc())

    result = await db.execute(query)
    rows = result.all()

    # Group by brigade
    brigade_data: Dict[str, Dict] = {}
    for row in rows:
        brigade_key = str(row[0])
        if brigade_key not in brigade_data:
            brigade_data[brigade_key] = {
                "brigade_id": brigade_key,
                "brigade_name": row[1],
                "scores": [],
            }
        brigade_data[brigade_key]["scores"].append({
            "score_date": row[2].isoformat(),
            "score": float(row[3]) if row[3] else 0.0,
            "overall_score": float(row[4]) if row[4] else None,
            "formula_version": row[5],
        })

    return {
        "period": {
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "days": days,
        },
        "brigades": list(brigade_data.values()),
    }

