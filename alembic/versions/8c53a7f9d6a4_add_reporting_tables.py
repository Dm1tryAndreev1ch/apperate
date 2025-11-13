"""Add reporting and analytics tables

Revision ID: 8c53a7f9d6a4
Revises: b545057304d5
Create Date: 2025-11-13 12:34:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "8c53a7f9d6a4"
down_revision = "add_brigades_20251113"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    existing_enums = {
        row[0] for row in bind.execute(sa.text("SELECT typname FROM pg_type WHERE typtype = 'e'"))
    }

    def enum_type(name: str, *values: str) -> sa.Enum:
        create_flag = name not in existing_enums
        enum_obj = sa.Enum(*values, name=name, create_type=create_flag)
        if create_flag:
            enum_obj.create(bind, checkfirst=True)
        return enum_obj

    calculationruntype = enum_type(
        "calculationruntype",
        "daily",
        "monthly",
        "equipment",
        "historical",
        "realtime",
    )
    calculationrunstatus = enum_type(
        "calculationrunstatus",
        "RUNNING",
        "SUCCESS",
        "FAILED",
    )
    dataqualityseverity = enum_type("dataqualityseverity", "INFO", "WARNING", "ERROR")
    dataqualityissuetype = enum_type(
        "dataqualityissuetype",
        "RANGE",
        "MISSING",
        "DUPLICATE",
        "SCHEMA",
        "CONSISTENCY",
    )
    remarkseverity = enum_type("remarkseverity", "LOW", "MEDIUM", "HIGH", "CRITICAL")
    equipmentstatus = enum_type(
        "equipmentstatus",
        "OK",
        "WARNING",
        "CRITICAL",
        "OUT_OF_SERVICE",
    )

    if "data_calculation_runs" not in existing_tables:
        op.create_table(
            "data_calculation_runs",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("run_type", calculationruntype, nullable=False),
            sa.Column("version", sa.String(length=32), nullable=False, server_default="v1"),
            sa.Column("label", sa.String(length=128), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=True),
            sa.Column("period_end", sa.Date(), nullable=True),
            sa.Column("triggered_by", sa.String(length=64), nullable=True),
            sa.Column("run_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("status", calculationrunstatus, nullable=False, server_default="RUNNING"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_data_calculation_runs_id"), "data_calculation_runs", ["id"], unique=False)
        op.create_index(op.f("ix_data_calculation_runs_run_type"), "data_calculation_runs", ["run_type"], unique=False)
        op.create_index(op.f("ix_data_calculation_runs_period_start"), "data_calculation_runs", ["period_start"], unique=False)
        op.create_index(op.f("ix_data_calculation_runs_period_end"), "data_calculation_runs", ["period_end"], unique=False)

    if "data_quality_issues" not in existing_tables:
        op.create_table(
            "data_quality_issues",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("calculation_run_id", sa.UUID(), nullable=False),
            sa.Column("entity_type", sa.String(length=64), nullable=False),
            sa.Column("entity_id", sa.String(length=64), nullable=True),
            sa.Column("issue_type", dataqualityissuetype, nullable=False),
            sa.Column("severity", dataqualityseverity, nullable=False, server_default="WARNING"),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("resolution", sa.Text(), nullable=True),
            sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(
                ["calculation_run_id"],
                ["data_calculation_runs.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_data_quality_issues_id"), "data_quality_issues", ["id"], unique=False)
        op.create_index(op.f("ix_data_quality_issues_calculation_run_id"), "data_quality_issues", ["calculation_run_id"], unique=False)
        op.create_index(op.f("ix_data_quality_issues_entity_type"), "data_quality_issues", ["entity_type"], unique=False)
        op.create_index(op.f("ix_data_quality_issues_issue_type"), "data_quality_issues", ["issue_type"], unique=False)
        op.create_index(op.f("ix_data_quality_issues_severity"), "data_quality_issues", ["severity"], unique=False)

    if "remark_entries" not in existing_tables:
        op.create_table(
            "remark_entries",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("check_instance_id", sa.UUID(), nullable=True),
            sa.Column("department_id", sa.String(length=255), nullable=True),
            sa.Column("brigade_id", sa.UUID(), nullable=True),
            sa.Column("block_code", sa.String(length=16), nullable=True),
            sa.Column("severity", remarkseverity, nullable=False, server_default="MEDIUM"),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("raised_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source", sa.String(length=64), nullable=False, server_default="manual"),
            sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["brigade_id"], ["brigades.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["check_instance_id"], ["check_instances.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_remark_entries_id"), "remark_entries", ["id"], unique=False)
        op.create_index(op.f("ix_remark_entries_check_instance_id"), "remark_entries", ["check_instance_id"], unique=False)
        op.create_index(op.f("ix_remark_entries_department_id"), "remark_entries", ["department_id"], unique=False)
        op.create_index(op.f("ix_remark_entries_brigade_id"), "remark_entries", ["brigade_id"], unique=False)
        op.create_index(op.f("ix_remark_entries_block_code"), "remark_entries", ["block_code"], unique=False)
        op.create_index(op.f("ix_remark_entries_raised_at"), "remark_entries", ["raised_at"], unique=False)

    if "equipment_register_entries" not in existing_tables:
        op.create_table(
            "equipment_register_entries",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("equipment_id", sa.String(length=128), nullable=False),
            sa.Column("department_id", sa.String(length=255), nullable=True),
            sa.Column("block_code", sa.String(length=16), nullable=True),
            sa.Column("status", equipmentstatus, nullable=False, server_default="OK"),
            sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("next_maintenance_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("responsible_user_id", sa.UUID(), nullable=True),
            sa.Column("attributes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.ForeignKeyConstraint(["responsible_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_equipment_register_entries_id"), "equipment_register_entries", ["id"], unique=False)
        op.create_index(op.f("ix_equipment_register_entries_equipment_id"), "equipment_register_entries", ["equipment_id"], unique=False)
        op.create_index(op.f("ix_equipment_register_entries_department_id"), "equipment_register_entries", ["department_id"], unique=False)
        op.create_index(op.f("ix_equipment_register_entries_block_code"), "equipment_register_entries", ["block_code"], unique=False)
        op.create_index(op.f("ix_equipment_register_entries_is_active"), "equipment_register_entries", ["is_active"], unique=False)

    if "daily_checklist_metrics" not in existing_tables:
        op.create_table(
            "daily_checklist_metrics",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("calculation_run_id", sa.UUID(), nullable=True),
            sa.Column("check_instance_id", sa.UUID(), nullable=False),
            sa.Column("score_date", sa.Date(), nullable=False),
            sa.Column("department_id", sa.String(length=255), nullable=True),
            sa.Column("brigade_id", sa.UUID(), nullable=True),
            sa.Column("block_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
            sa.Column("comment_threads", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("remark_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("equipment_alerts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["brigade_id"], ["brigades.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["calculation_run_id"], ["data_calculation_runs.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["check_instance_id"], ["check_instances.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("check_instance_id", name="uq_daily_metric_check_instance"),
        )
        op.create_index(op.f("ix_daily_checklist_metrics_id"), "daily_checklist_metrics", ["id"], unique=False)
        op.create_index(op.f("ix_daily_checklist_metrics_calculation_run_id"), "daily_checklist_metrics", ["calculation_run_id"], unique=False)
        op.create_index(op.f("ix_daily_checklist_metrics_check_instance_id"), "daily_checklist_metrics", ["check_instance_id"], unique=False)
        op.create_index(op.f("ix_daily_checklist_metrics_score_date"), "daily_checklist_metrics", ["score_date"], unique=False)
        op.create_index(op.f("ix_daily_checklist_metrics_department_id"), "daily_checklist_metrics", ["department_id"], unique=False)
        op.create_index(op.f("ix_daily_checklist_metrics_brigade_id"), "daily_checklist_metrics", ["brigade_id"], unique=False)

    if "department_monthly_summaries" not in existing_tables:
        op.create_table(
            "department_monthly_summaries",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("calculation_run_id", sa.UUID(), nullable=False),
            sa.Column("department_id", sa.String(length=255), nullable=False),
            sa.Column("month", sa.Date(), nullable=False),
            sa.Column("avg_score", sa.Numeric(5, 2), nullable=False),
            sa.Column("mom_delta", sa.Numeric(6, 2), nullable=True),
            sa.Column("ytd_delta", sa.Numeric(6, 2), nullable=True),
            sa.Column("rank_position", sa.Integer(), nullable=True),
            sa.Column("check_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("rolling_average", sa.Numeric(5, 2), nullable=True),
            sa.Column("trend_series", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("remarks_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["calculation_run_id"], ["data_calculation_runs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("department_id", "month", "calculation_run_id", name="uq_department_month_run"),
        )
        op.create_index(op.f("ix_department_monthly_summaries_id"), "department_monthly_summaries", ["id"], unique=False)
        op.create_index(
            op.f("ix_department_monthly_summaries_calculation_run_id"),
            "department_monthly_summaries",
            ["calculation_run_id"],
            unique=False,
        )
        op.create_index(op.f("ix_department_monthly_summaries_department_id"), "department_monthly_summaries", ["department_id"], unique=False)
        op.create_index(op.f("ix_department_monthly_summaries_month"), "department_monthly_summaries", ["month"], unique=False)

    if "equipment_status_snapshots" not in existing_tables:
        op.create_table(
            "equipment_status_snapshots",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("calculation_run_id", sa.UUID(), nullable=False),
            sa.Column("department_id", sa.String(length=255), nullable=False),
            sa.Column("month", sa.Date(), nullable=False),
            sa.Column("block_code", sa.String(length=16), nullable=False),
            sa.Column("aggregated_score", sa.Numeric(5, 2), nullable=True),
            sa.Column("equipment_total", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("equipment_warning", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("equipment_critical", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("downtime_hours", sa.Numeric(12, 2), nullable=True),
            sa.Column("notes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["calculation_run_id"], ["data_calculation_runs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("department_id", "month", "block_code", "calculation_run_id", name="uq_equipment_snapshot"),
        )
        op.create_index(op.f("ix_equipment_status_snapshots_id"), "equipment_status_snapshots", ["id"], unique=False)
        op.create_index(
            op.f("ix_equipment_status_snapshots_calculation_run_id"),
            "equipment_status_snapshots",
            ["calculation_run_id"],
            unique=False,
        )
        op.create_index(op.f("ix_equipment_status_snapshots_department_id"), "equipment_status_snapshots", ["department_id"], unique=False)
        op.create_index(op.f("ix_equipment_status_snapshots_month"), "equipment_status_snapshots", ["month"], unique=False)
        op.create_index(op.f("ix_equipment_status_snapshots_block_code"), "equipment_status_snapshots", ["block_code"], unique=False)

    if "department_historical_comparisons" not in existing_tables:
        op.create_table(
            "department_historical_comparisons",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("calculation_run_id", sa.UUID(), nullable=False),
            sa.Column("department_id", sa.String(length=255), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("avg_score", sa.Numeric(5, 2), nullable=False),
            sa.Column("delta_vs_prev", sa.Numeric(6, 2), nullable=True),
            sa.Column("best_block", sa.String(length=16), nullable=True),
            sa.Column("risk_block", sa.String(length=16), nullable=True),
            sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["calculation_run_id"], ["data_calculation_runs.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("department_id", "year", "calculation_run_id", name="uq_department_year_run"),
        )
        op.create_index(op.f("ix_department_historical_comparisons_id"), "department_historical_comparisons", ["id"], unique=False)
        op.create_index(
            op.f("ix_department_historical_comparisons_calculation_run_id"),
            "department_historical_comparisons",
            ["calculation_run_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_department_historical_comparisons_department_id"),
            "department_historical_comparisons",
            ["department_id"],
            unique=False,
        )
        op.create_index(op.f("ix_department_historical_comparisons_year"), "department_historical_comparisons", ["year"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_department_historical_comparisons_year"), table_name="department_historical_comparisons")
    op.drop_index(op.f("ix_department_historical_comparisons_department_id"), table_name="department_historical_comparisons")
    op.drop_index(
        op.f("ix_department_historical_comparisons_calculation_run_id"),
        table_name="department_historical_comparisons",
    )
    op.drop_index(op.f("ix_department_historical_comparisons_id"), table_name="department_historical_comparisons")
    op.drop_table("department_historical_comparisons")

    op.drop_index(op.f("ix_equipment_status_snapshots_block_code"), table_name="equipment_status_snapshots")
    op.drop_index(op.f("ix_equipment_status_snapshots_month"), table_name="equipment_status_snapshots")
    op.drop_index(op.f("ix_equipment_status_snapshots_department_id"), table_name="equipment_status_snapshots")
    op.drop_index(op.f("ix_equipment_status_snapshots_calculation_run_id"), table_name="equipment_status_snapshots")
    op.drop_index(op.f("ix_equipment_status_snapshots_id"), table_name="equipment_status_snapshots")
    op.drop_table("equipment_status_snapshots")

    op.drop_index(op.f("ix_department_monthly_summaries_month"), table_name="department_monthly_summaries")
    op.drop_index(op.f("ix_department_monthly_summaries_department_id"), table_name="department_monthly_summaries")
    op.drop_index(
        op.f("ix_department_monthly_summaries_calculation_run_id"),
        table_name="department_monthly_summaries",
    )
    op.drop_index(op.f("ix_department_monthly_summaries_id"), table_name="department_monthly_summaries")
    op.drop_table("department_monthly_summaries")

    op.drop_index(op.f("ix_daily_checklist_metrics_brigade_id"), table_name="daily_checklist_metrics")
    op.drop_index(op.f("ix_daily_checklist_metrics_department_id"), table_name="daily_checklist_metrics")
    op.drop_index(op.f("ix_daily_checklist_metrics_score_date"), table_name="daily_checklist_metrics")
    op.drop_index(op.f("ix_daily_checklist_metrics_check_instance_id"), table_name="daily_checklist_metrics")
    op.drop_index(op.f("ix_daily_checklist_metrics_calculation_run_id"), table_name="daily_checklist_metrics")
    op.drop_index(op.f("ix_daily_checklist_metrics_id"), table_name="daily_checklist_metrics")
    op.drop_table("daily_checklist_metrics")

    op.drop_index(op.f("ix_equipment_register_entries_is_active"), table_name="equipment_register_entries")
    op.drop_index(op.f("ix_equipment_register_entries_block_code"), table_name="equipment_register_entries")
    op.drop_index(op.f("ix_equipment_register_entries_department_id"), table_name="equipment_register_entries")
    op.drop_index(op.f("ix_equipment_register_entries_equipment_id"), table_name="equipment_register_entries")
    op.drop_index(op.f("ix_equipment_register_entries_id"), table_name="equipment_register_entries")
    op.drop_table("equipment_register_entries")

    op.drop_index(op.f("ix_remark_entries_raised_at"), table_name="remark_entries")
    op.drop_index(op.f("ix_remark_entries_block_code"), table_name="remark_entries")
    op.drop_index(op.f("ix_remark_entries_brigade_id"), table_name="remark_entries")
    op.drop_index(op.f("ix_remark_entries_department_id"), table_name="remark_entries")
    op.drop_index(op.f("ix_remark_entries_check_instance_id"), table_name="remark_entries")
    op.drop_index(op.f("ix_remark_entries_id"), table_name="remark_entries")
    op.drop_table("remark_entries")

    op.drop_index(op.f("ix_data_quality_issues_severity"), table_name="data_quality_issues")
    op.drop_index(op.f("ix_data_quality_issues_issue_type"), table_name="data_quality_issues")
    op.drop_index(op.f("ix_data_quality_issues_entity_type"), table_name="data_quality_issues")
    op.drop_index(op.f("ix_data_quality_issues_calculation_run_id"), table_name="data_quality_issues")
    op.drop_index(op.f("ix_data_quality_issues_id"), table_name="data_quality_issues")
    op.drop_table("data_quality_issues")

    op.drop_index(op.f("ix_data_calculation_runs_period_end"), table_name="data_calculation_runs")
    op.drop_index(op.f("ix_data_calculation_runs_period_start"), table_name="data_calculation_runs")
    op.drop_index(op.f("ix_data_calculation_runs_run_type"), table_name="data_calculation_runs")
    op.drop_index(op.f("ix_data_calculation_runs_id"), table_name="data_calculation_runs")
    op.drop_table("data_calculation_runs")

    equipmentstatus = sa.Enum(
        "OK",
        "WARNING",
        "CRITICAL",
        "OUT_OF_SERVICE",
        name="equipmentstatus",
    )
    remarkseverity = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="remarkseverity")
    dataqualityissuetype = sa.Enum(
        "RANGE",
        "MISSING",
        "DUPLICATE",
        "SCHEMA",
        "CONSISTENCY",
        name="dataqualityissuetype",
    )
    dataqualityseverity = sa.Enum("INFO", "WARNING", "ERROR", name="dataqualityseverity")
    calculationrunstatus = sa.Enum("RUNNING", "SUCCESS", "FAILED", name="calculationrunstatus")
    calculationruntype = sa.Enum(
        "daily",
        "monthly",
        "equipment",
        "historical",
        "realtime",
        name="calculationruntype",
    )

    bind = op.get_bind()
    equipmentstatus.drop(bind, checkfirst=True)
    remarkseverity.drop(bind, checkfirst=True)
    dataqualityissuetype.drop(bind, checkfirst=True)
    dataqualityseverity.drop(bind, checkfirst=True)
    calculationrunstatus.drop(bind, checkfirst=True)
    calculationruntype.drop(bind, checkfirst=True)

