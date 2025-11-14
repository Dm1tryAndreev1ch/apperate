"""Analytics service for aggregating data and computing KPIs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.checklist import CheckInstance, CheckStatus
from app.models.report import Report, ReportStatus
from app.models.reporting import (
    DailyChecklistMetric,
    DepartmentMonthlySummary,
    RemarkEntry,
    RemarkSeverity,
)
from app.models.user import User
from app.services.checklist_service import checklist_service


@dataclass
class BrigadeScoreDTO:
    """Brigade score data transfer object."""

    brigade_id: UUID
    brigade_name: str
    score_date: date
    score: Decimal
    overall_score: Optional[Decimal]
    formula_version: str
    details: Dict[str, Any]


@dataclass
class AlertDTO:
    """Alert/anomaly data transfer object."""

    severity: str  # "WARNING", "ERROR", "CRITICAL"
    category: str  # "failed_check", "low_score", "data_quality", "equipment"
    message: str
    check_instance_id: Optional[UUID] = None
    brigade_id: Optional[UUID] = None
    department_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ReportAnalyticsDTO:
    """Aggregated analytics for a report."""

    check_instance_id: UUID
    avg_score: Optional[Decimal]
    brigade_score: Optional[BrigadeScoreDTO]
    remark_count: int
    critical_violations: List[Dict[str, Any]]
    alerts: List[AlertDTO]
    equipment_alerts: List[Dict[str, Any]]
    period_deltas: Optional[Dict[str, Decimal]] = None


@dataclass
class PeriodSummaryDTO:
    """Period summary data transfer object."""

    granularity: str  # "day", "week", "month"
    period_start: date
    period_end: date
    report_count: int
    avg_score: Optional[Decimal]
    brigade_scores: List[BrigadeScoreDTO]
    remark_count: int
    delta_metrics: Dict[str, Decimal]
    department_breakdown: Dict[str, Any]


class AnalyticsService:
    """Service for computing analytics and KPIs."""

    @staticmethod
    async def compute_brigade_score(
        db: AsyncSession,
        *,
        brigade_id: UUID,
        score_date: date,
        check_instance_id: Optional[UUID] = None,
    ) -> Optional[BrigadeScoreDTO]:
        """Compute or retrieve brigade daily score."""
        result = await db.execute(
            select(BrigadeDailyScore)
            .where(
                BrigadeDailyScore.brigade_id == brigade_id,
                BrigadeDailyScore.score_date == score_date,
            )
            .options(selectinload(BrigadeDailyScore.brigade))
        )
        score_obj = result.scalar_one_or_none()

        if score_obj:
            return BrigadeScoreDTO(
                brigade_id=score_obj.brigade_id,
                brigade_name=score_obj.brigade.name if score_obj.brigade else "Unknown",
                score_date=score_obj.score_date,
                score=Decimal(str(score_obj.score)),
                overall_score=Decimal(str(score_obj.overall_score)) if score_obj.overall_score else None,
                formula_version=score_obj.formula_version,
                details=score_obj.details or {},
            )
        return None

    @staticmethod
    async def compute_report_analytics(
        db: AsyncSession,
        *,
        check_instance: CheckInstance,
    ) -> ReportAnalyticsDTO:
        """Compute analytics for a specific check instance."""
        template_schema = check_instance.template.schema if check_instance.template else {}
        answers = check_instance.answers or {}

        # Calculate score
        score = checklist_service.calculate_score(template_schema, answers)

        # Find critical violations
        violations = checklist_service.find_critical_violations(template_schema, answers)

        # Get brigade score if available
        brigade_score_dto = None
        if check_instance.brigade_id and check_instance.finished_at:
            score_date = check_instance.finished_at.date()
            brigade_score_dto = await AnalyticsService.compute_brigade_score(
                db,
                brigade_id=check_instance.brigade_id,
                score_date=score_date,
                check_instance_id=check_instance.id,
            )

        # Count remarks
        remark_result = await db.execute(
            select(func.count(RemarkEntry.id)).where(
                RemarkEntry.check_instance_id == check_instance.id
            )
        )
        remark_count = remark_result.scalar_one_or_none() or 0

        # Build alerts
        alerts: List[AlertDTO] = []
        if violations:
            for violation in violations:
                alerts.append(
                    AlertDTO(
                        severity="CRITICAL",
                        category="failed_check",
                        message=f"Critical violation: {violation.get('question_text', 'Unknown')}",
                        check_instance_id=check_instance.id,
                        brigade_id=check_instance.brigade_id,
                        department_id=check_instance.department_id,
                        metadata=violation,
                    )
                )

        if brigade_score_dto and brigade_score_dto.score < Decimal("70.0"):
            alerts.append(
                AlertDTO(
                    severity="WARNING",
                    category="low_score",
                    message=f"Brigade score below threshold: {brigade_score_dto.score}",
                    brigade_id=check_instance.brigade_id,
                    department_id=check_instance.department_id,
                    metadata={"score": float(brigade_score_dto.score)},
                )
            )

        # Equipment alerts (placeholder - can be enhanced)
        equipment_alerts: List[Dict[str, Any]] = []

        return ReportAnalyticsDTO(
            check_instance_id=check_instance.id,
            avg_score=Decimal(str(score)),
            brigade_score=brigade_score_dto,
            remark_count=remark_count,
            critical_violations=violations,
            alerts=alerts,
            equipment_alerts=equipment_alerts,
        )

    @staticmethod
    async def compute_period_summary(
        db: AsyncSession,
        *,
        granularity: str,
        period_start: date,
        period_end: date,
        department_id: Optional[str] = None,
        brigade_id: Optional[UUID] = None,
        author_id: Optional[UUID] = None,
    ) -> PeriodSummaryDTO:
        """Compute summary for a time period."""
        # Build query filters
        check_filters = [
            CheckInstance.status == CheckStatus.COMPLETED,
            CheckInstance.finished_at.isnot(None),
        ]
        if department_id:
            check_filters.append(CheckInstance.department_id == department_id)
        if brigade_id:
            check_filters.append(CheckInstance.brigade_id == brigade_id)

        # Get reports in period
        report_filters = [
            Report.status == ReportStatus.READY,
            Report.created_at >= datetime.combine(period_start, datetime.min.time()),
            Report.created_at <= datetime.combine(period_end, datetime.max.time()),
        ]
        if author_id:
            report_filters.append(Report.author_id == author_id)

        report_result = await db.execute(
            select(func.count(Report.id)).where(*report_filters)
        )
        report_count = report_result.scalar_one_or_none() or 0

        # Get average scores from daily metrics
        metric_filters = [
            DailyChecklistMetric.score_date >= period_start,
            DailyChecklistMetric.score_date <= period_end,
        ]
        if department_id:
            metric_filters.append(DailyChecklistMetric.department_id == department_id)
        if brigade_id:
            metric_filters.append(DailyChecklistMetric.brigade_id == brigade_id)

        avg_result = await db.execute(
            select(func.avg(DailyChecklistMetric.overall_score)).where(*metric_filters)
        )
        avg_score = avg_result.scalar_one_or_none()
        avg_score_decimal = Decimal(str(avg_score)) if avg_score else None

        # Get brigade scores
        brigade_scores: List[BrigadeScoreDTO] = []
        if brigade_id:
            score_result = await db.execute(
                select(BrigadeDailyScore)
                .where(
                    BrigadeDailyScore.brigade_id == brigade_id,
                    BrigadeDailyScore.score_date >= period_start,
                    BrigadeDailyScore.score_date <= period_end,
                )
                .options(selectinload(BrigadeDailyScore.brigade))
            )
            for score_obj in score_result.scalars().all():
                brigade_scores.append(
                    BrigadeScoreDTO(
                        brigade_id=score_obj.brigade_id,
                        brigade_name=score_obj.brigade.name if score_obj.brigade else "Unknown",
                        score_date=score_obj.score_date,
                        score=Decimal(str(score_obj.score)),
                        overall_score=Decimal(str(score_obj.overall_score)) if score_obj.overall_score else None,
                        formula_version=score_obj.formula_version,
                        details=score_obj.details or {},
                    )
                )

        # Count remarks
        remark_filters = [
            RemarkEntry.raised_at >= datetime.combine(period_start, datetime.min.time()),
            RemarkEntry.raised_at <= datetime.combine(period_end, datetime.max.time()),
        ]
        if department_id:
            remark_filters.append(RemarkEntry.department_id == department_id)
        if brigade_id:
            remark_filters.append(RemarkEntry.brigade_id == brigade_id)

        remark_result = await db.execute(
            select(func.count(RemarkEntry.id)).where(*remark_filters)
        )
        remark_count = remark_result.scalar_one_or_none() or 0

        # Compute deltas (compare with previous period)
        period_duration = (period_end - period_start).days + 1
        prev_period_start = period_start - timedelta(days=period_duration)
        prev_period_end = period_start - timedelta(days=1)

        prev_avg_result = await db.execute(
            select(func.avg(DailyChecklistMetric.overall_score)).where(
                DailyChecklistMetric.score_date >= prev_period_start,
                DailyChecklistMetric.score_date <= prev_period_end,
                *([DailyChecklistMetric.department_id == department_id] if department_id else []),
                *([DailyChecklistMetric.brigade_id == brigade_id] if brigade_id else []),
            )
        )
        prev_avg = prev_avg_result.scalar_one_or_none()
        prev_avg_decimal = Decimal(str(prev_avg)) if prev_avg else None

        delta_metrics: Dict[str, Decimal] = {}
        if avg_score_decimal is not None and prev_avg_decimal is not None:
            delta_metrics["score_delta"] = avg_score_decimal - prev_avg_decimal

        # Department breakdown (simplified)
        department_breakdown: Dict[str, Any] = {}

        return PeriodSummaryDTO(
            granularity=granularity,
            period_start=period_start,
            period_end=period_end,
            report_count=report_count,
            avg_score=avg_score_decimal,
            brigade_scores=brigade_scores,
            remark_count=remark_count,
            delta_metrics=delta_metrics,
            department_breakdown=department_breakdown,
        )

    @staticmethod
    async def get_brigade_scores_for_period(
        db: AsyncSession,
        *,
        period_start: date,
        period_end: date,
        brigade_ids: Optional[List[UUID]] = None,
    ) -> List[BrigadeScoreDTO]:
        """Get all brigade scores for a period."""
        filters = [
            BrigadeDailyScore.score_date >= period_start,
            BrigadeDailyScore.score_date <= period_end,
        ]
        if brigade_ids:
            filters.append(BrigadeDailyScore.brigade_id.in_(brigade_ids))

        result = await db.execute(
            select(BrigadeDailyScore)
            .where(*filters)
            .options(selectinload(BrigadeDailyScore.brigade))
            .order_by(BrigadeDailyScore.brigade_id, BrigadeDailyScore.score_date)
        )

        scores: List[BrigadeScoreDTO] = []
        for score_obj in result.scalars().all():
            scores.append(
                BrigadeScoreDTO(
                    brigade_id=score_obj.brigade_id,
                    brigade_name=score_obj.brigade.name if score_obj.brigade else "Unknown",
                    score_date=score_obj.score_date,
                    score=Decimal(str(score_obj.score)),
                    overall_score=Decimal(str(score_obj.overall_score)) if score_obj.overall_score else None,
                    formula_version=score_obj.formula_version,
                    details=score_obj.details or {},
                )
            )
        return scores


analytics_service = AnalyticsService()

