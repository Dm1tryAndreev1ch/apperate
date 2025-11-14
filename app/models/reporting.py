"""Reporting and analytics domain models."""
from __future__ import annotations

import uuid
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.db.types import GUID, JSONBType


class CalculationRunType(str, Enum):
    """Types of scheduled analytics calculation runs."""

    DAILY = "daily"
    MONTHLY = "monthly"
    EQUIPMENT = "equipment"
    HISTORICAL = "historical"
    REALTIME = "realtime"


class CalculationRunStatus(str, Enum):
    """Status of an analytics calculation run."""

    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class DataCalculationRun(Base):
    """Metadata for analytics calculation runs allowing reproducibility and versioning."""

    __tablename__ = "data_calculation_runs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    run_type = Column(SQLEnum(CalculationRunType), nullable=False, index=True)
    version = Column(String(32), nullable=False, default="v1")
    label = Column(String(128), nullable=False)
    period_start = Column(Date, nullable=True, index=True)
    period_end = Column(Date, nullable=True, index=True)
    triggered_by = Column(String(64), nullable=True)
    run_metadata = Column(JSONBType(), nullable=True, default=dict)
    status = Column(SQLEnum(CalculationRunStatus), nullable=False, default=CalculationRunStatus.RUNNING)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    daily_metrics = relationship(
        "DailyChecklistMetric",
        back_populates="calculation_run",
        cascade="all, delete-orphan",
    )
    monthly_summaries = relationship(
        "DepartmentMonthlySummary",
        back_populates="calculation_run",
        cascade="all, delete-orphan",
    )
    equipment_snapshots = relationship(
        "EquipmentStatusSnapshot",
        back_populates="calculation_run",
        cascade="all, delete-orphan",
    )
    yearly_comparisons = relationship(
        "DepartmentHistoricalComparison",
        back_populates="calculation_run",
        cascade="all, delete-orphan",
    )
    data_quality_issues = relationship(
        "DataQualityIssue",
        back_populates="calculation_run",
        cascade="all, delete-orphan",
    )


class DataQualitySeverity(str, Enum):
    """Severity of data quality issues."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class DataQualityIssueType(str, Enum):
    """Categorisation for data quality issues."""

    RANGE = "RANGE"
    MISSING = "MISSING"
    DUPLICATE = "DUPLICATE"
    SCHEMA = "SCHEMA"
    CONSISTENCY = "CONSISTENCY"


class DataQualityIssue(Base):
    """Logged data quality issue detected during ETL validation."""

    __tablename__ = "data_quality_issues"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    calculation_run_id = Column(
        GUID(),
        ForeignKey("data_calculation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(64), nullable=True)
    issue_type = Column(SQLEnum(DataQualityIssueType), nullable=False)
    severity = Column(SQLEnum(DataQualitySeverity), nullable=False, default=DataQualitySeverity.WARNING)
    description = Column(Text, nullable=False)
    resolution = Column(Text, nullable=True)
    details = Column(JSONBType(), nullable=True, default=dict)
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    calculation_run = relationship("DataCalculationRun", back_populates="data_quality_issues")


class RemarkSeverity(str, Enum):
    """Severity levels for remark journal entries."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RemarkEntry(Base):
    """Remark journal entry captured during inspections or audits."""

    __tablename__ = "remark_entries"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    check_instance_id = Column(
        GUID(),
        ForeignKey("check_instances.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    department_id = Column(String(255), nullable=True, index=True)
    brigade_id = Column(GUID(), ForeignKey("brigades.id", ondelete="SET NULL"), nullable=True, index=True)
    block_code = Column(String(16), nullable=True, index=True)
    severity = Column(SQLEnum(RemarkSeverity), nullable=False, default=RemarkSeverity.MEDIUM)
    message = Column(Text, nullable=False)
    raised_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(64), nullable=False, default="manual")
    details = Column(JSONBType(), nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class EquipmentStatus(str, Enum):
    """Qualitative equipment status."""

    OK = "OK"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class EquipmentRegisterEntry(Base):
    """Equipment register snapshot (raw source for equipment status reporting)."""

    __tablename__ = "equipment_register_entries"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    equipment_id = Column(String(128), nullable=False, index=True)
    department_id = Column(String(255), nullable=True, index=True)
    block_code = Column(String(16), nullable=True, index=True)
    status = Column(SQLEnum(EquipmentStatus), nullable=False, default=EquipmentStatus.OK)
    last_checked_at = Column(DateTime(timezone=True), nullable=False)
    next_maintenance_at = Column(DateTime(timezone=True), nullable=True)
    responsible_user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    attributes = Column(JSONBType(), nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True, index=True)


class DailyChecklistMetric(Base):
    """Daily fact table for checklist block-level scores."""

    __tablename__ = "daily_checklist_metrics"
    __table_args__ = (
        UniqueConstraint("check_instance_id", name="uq_daily_metric_check_instance"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    calculation_run_id = Column(
        GUID(),
        ForeignKey("data_calculation_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    check_instance_id = Column(
        GUID(),
        ForeignKey("check_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score_date = Column(Date, nullable=False, index=True)
    department_id = Column(String(255), nullable=True, index=True)
    brigade_id = Column(GUID(), ForeignKey("brigades.id", ondelete="SET NULL"), nullable=True, index=True)
    block_scores = Column(JSONBType(), nullable=False, default=dict)
    overall_score = Column(Numeric(5, 2), nullable=True)
    comment_threads = Column(JSONBType(), nullable=True)
    remark_count = Column(Integer, nullable=False, default=0)
    equipment_alerts = Column(JSONBType(), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    calculation_run = relationship("DataCalculationRun", back_populates="daily_metrics")


class DepartmentMonthlySummary(Base):
    """Aggregated monthly metrics per department with rankings and dynamics."""

    __tablename__ = "department_monthly_summaries"
    __table_args__ = (
        UniqueConstraint("department_id", "month", "calculation_run_id", name="uq_department_month_run"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    calculation_run_id = Column(
        GUID(),
        ForeignKey("data_calculation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department_id = Column(String(255), nullable=False, index=True)
    month = Column(Date, nullable=False, index=True)
    avg_score = Column(Numeric(5, 2), nullable=False)
    mom_delta = Column(Numeric(6, 2), nullable=True)
    ytd_delta = Column(Numeric(6, 2), nullable=True)
    rank_position = Column(Integer, nullable=True)
    check_count = Column(Integer, nullable=False, default=0)
    rolling_average = Column(Numeric(5, 2), nullable=True)
    trend_series = Column(JSONBType(), nullable=True)
    remarks_breakdown = Column(JSONBType(), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    calculation_run = relationship("DataCalculationRun", back_populates="monthly_summaries")


class EquipmentStatusSnapshot(Base):
    """Monthly aggregated equipment status metrics focusing on B/B2 blocks."""

    __tablename__ = "equipment_status_snapshots"
    __table_args__ = (
        UniqueConstraint("department_id", "month", "block_code", "calculation_run_id", name="uq_equipment_snapshot"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    calculation_run_id = Column(
        GUID(),
        ForeignKey("data_calculation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department_id = Column(String(255), nullable=False, index=True)
    month = Column(Date, nullable=False, index=True)
    block_code = Column(String(16), nullable=False, index=True)
    aggregated_score = Column(Numeric(5, 2), nullable=True)
    equipment_total = Column(Integer, nullable=False, default=0)
    equipment_warning = Column(Integer, nullable=False, default=0)
    equipment_critical = Column(Integer, nullable=False, default=0)
    downtime_hours = Column(Numeric(12, 2), nullable=True)
    notes = Column(JSONBType(), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    calculation_run = relationship("DataCalculationRun", back_populates="equipment_snapshots")


class DepartmentHistoricalComparison(Base):
    """Aggregated yearly metrics for cross-year comparisons."""

    __tablename__ = "department_historical_comparisons"
    __table_args__ = (
        UniqueConstraint("department_id", "year", "calculation_run_id", name="uq_department_year_run"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    calculation_run_id = Column(
        GUID(),
        ForeignKey("data_calculation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department_id = Column(String(255), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    avg_score = Column(Numeric(5, 2), nullable=False)
    delta_vs_prev = Column(Numeric(6, 2), nullable=True)
    best_block = Column(String(16), nullable=True)
    risk_block = Column(String(16), nullable=True)
    summary = Column(JSONBType(), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    calculation_run = relationship("DataCalculationRun", back_populates="yearly_comparisons")


class PeriodSummaryGranularity(str, Enum):
    """Supported period granularities for report summaries."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class ReportPeriodSummary(Base):
    """Precomputed aggregates for dashboards and Excel exports."""

    __tablename__ = "report_period_summaries"
    __table_args__ = (
        UniqueConstraint(
            "granularity",
            "period_start",
            "period_end",
            "department_id",
            "brigade_id",
            "author_id",
            name="uq_report_summary_scope",
        ),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    granularity = Column(SQLEnum(PeriodSummaryGranularity), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    department_id = Column(String(255), nullable=True, index=True)
    brigade_id = Column(GUID(), ForeignKey("brigades.id", ondelete="SET NULL"), nullable=True, index=True)
    author_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    report_count = Column(Integer, nullable=False, default=0)
    summary_metrics = Column(JSONBType(), nullable=False, default=dict)
    delta_metrics = Column(JSONBType(), nullable=True, default=dict)
    filters = Column(JSONBType(), nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class ReportGenerationEventType(str, Enum):
    """Types of report generation events."""

    MANUAL = "manual"
    SCHEDULED = "scheduled"
    RETRY = "retry"
    ALERT = "alert"


class ReportGenerationStatus(str, Enum):
    """Status for report generation events."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ReportGenerationEvent(Base):
    """History of report generation attempts (manual or scheduled)."""

    __tablename__ = "report_generation_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    report_id = Column(GUID(), ForeignKey("reports.id", ondelete="CASCADE"), nullable=True, index=True)
    check_instance_id = Column(GUID(), ForeignKey("check_instances.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(SQLEnum(ReportGenerationEventType), nullable=False, index=True)
    status = Column(SQLEnum(ReportGenerationStatus), nullable=False, default=ReportGenerationStatus.PENDING, index=True)
    triggered_by = Column(String(128), nullable=True)
    payload = Column(JSONBType(), nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    report = relationship("Report", back_populates="generation_events")
    check_instance = relationship("CheckInstance")


