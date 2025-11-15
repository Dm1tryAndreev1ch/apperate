"""MantaQC schema updates for XLSX-only reporting and analytics extensions.

Revision ID: mantaqc_schema_20251114
Revises: 8c53a7f9d6a4
Create Date: 2025-11-14 13:30:00.000000
"""
from __future__ import annotations

import re
import unicodedata

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect, text

# revision identifiers, used by Alembic.
revision = "mantaqc_schema_20251114"
down_revision = "8c53a7f9d6a4"
branch_labels = None
depends_on = None


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    cleaned = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE)
    lowered = cleaned.strip().lower()
    slug = re.sub(r"[-\s_]+", "-", lowered).strip("-")
    return slug or "template"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "reports" in tables:
        # Check existing columns
        report_columns = {col["name"] for col in inspector.get_columns("reports")}
        
        # Add author + metadata columns if they don't exist
        if "author_id" not in report_columns:
            op.add_column("reports", sa.Column("author_id", sa.UUID(), nullable=True))
        if "metadata" not in report_columns:
            op.add_column(
                "reports",
                sa.Column(
                    "metadata",
                    postgresql.JSONB(astext_type=sa.Text()),
                    nullable=False,
                    server_default=sa.text("'{}'::jsonb"),
                ),
            )
        
        # Create index and foreign key if they don't exist
        indexes = {idx["name"] for idx in inspector.get_indexes("reports")}
        if "ix_reports_author_id" not in indexes:
            op.create_index(op.f("ix_reports_author_id"), "reports", ["author_id"], unique=False)
        
        foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("reports")}
        if "fk_reports_author_id" not in foreign_keys:
            op.create_foreign_key(
                "fk_reports_author_id",
                "reports",
                "users",
                ["author_id"],
                ["id"],
                ondelete="SET NULL",
            )
        
        op.execute(sa.text("UPDATE reports SET author_id = generated_by WHERE generated_by IS NOT NULL AND author_id IS NULL"))
        op.execute(sa.text("UPDATE reports SET metadata = '{}'::jsonb WHERE metadata IS NULL"))
        if "metadata" in report_columns:
            op.alter_column("reports", "metadata", server_default=None)

        # Transition enum to XLSX-only format
        # Check current column type
        format_column = next((col for col in inspector.get_columns("reports") if col["name"] == "format"), None)
        current_type = str(format_column["type"]) if format_column else None
        
        # Only migrate if not already migrated
        if current_type and "reportformatxlsx" not in current_type.lower():
            # First, add the new enum value in a separate transaction
            op.execute(sa.text("ALTER TYPE reportformat ADD VALUE IF NOT EXISTS 'xlsx'"))
            # Commit the enum change (PostgreSQL requires this)
            bind.commit()
            
            # Now update existing records to use 'xlsx' (convert all old formats)
            # Use text conversion to avoid type mismatch
            op.execute(sa.text("UPDATE reports SET format = 'xlsx'::text WHERE format IS NOT NULL"))
            
            # Create new enum first
            report_format_enum = postgresql.ENUM("xlsx", name="reportformatxlsx")
            report_format_enum.create(bind, checkfirst=True)
            
            # Convert to text temporarily
            op.execute(sa.text("ALTER TABLE reports ALTER COLUMN format TYPE text USING format::text"))
            # Ensure all values are 'xlsx' as text
            op.execute(sa.text("UPDATE reports SET format = 'xlsx' WHERE format IS NULL OR format != 'xlsx'"))
            # Now convert to new enum type using explicit cast
            op.execute(sa.text("ALTER TABLE reports ALTER COLUMN format TYPE reportformatxlsx USING ('xlsx'::reportformatxlsx)"))
            op.execute(sa.text("DROP TYPE IF EXISTS reportformat"))
        elif current_type and "reportformatxlsx" in current_type.lower():
            # Already migrated, just ensure all values are 'xlsx'
            op.execute(sa.text("UPDATE reports SET format = 'xlsx'::reportformatxlsx WHERE format IS NOT NULL AND format::text != 'xlsx'"))

    if "brigade_daily_scores" in tables:
        # Check existing columns
        brigade_score_columns = {col["name"] for col in inspector.get_columns("brigade_daily_scores")}
        
        if "overall_score" not in brigade_score_columns:
            op.add_column(
                "brigade_daily_scores",
                sa.Column("overall_score", sa.Numeric(6, 3), nullable=True),
            )
        if "formula_version" not in brigade_score_columns:
            op.add_column(
                "brigade_daily_scores",
                sa.Column("formula_version", sa.String(length=32), nullable=False, server_default="v1"),
            )

    if "checklist_templates" in tables:
        op.add_column(
            "checklist_templates",
            sa.Column("name_slug", sa.String(length=255), nullable=True),
        )
        op.add_column(
            "checklist_templates",
            sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

        result = bind.execute(text("SELECT id, name FROM checklist_templates"))
        existing_slugs = set()
        for row in result:
            base_slug = _slugify(row.name)
            candidate = base_slug
            suffix = 1
            while candidate in existing_slugs:
                suffix += 1
                candidate = f"{base_slug}-{suffix}"
            existing_slugs.add(candidate)
            bind.execute(
                text("UPDATE checklist_templates SET name_slug = :slug WHERE id = :id"),
                {"slug": candidate, "id": row.id},
            )
        op.alter_column(
            "checklist_templates",
            "name_slug",
            existing_type=sa.String(length=255),
            nullable=False,
        )
        op.create_index(
            op.f("ix_checklist_templates_name_slug"),
            "checklist_templates",
            ["name_slug"],
            unique=True,
        )

    # Create enums for new tables
    period_enum = postgresql.ENUM("day", "week", "month", name="periodsummarygranularity")
    period_enum.create(bind, checkfirst=True)
    event_type_enum = postgresql.ENUM("manual", "scheduled", "retry", "alert", name="reportgenerationeventtype")
    event_type_enum.create(bind, checkfirst=True)
    event_status_enum = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "SUCCESS",
        "FAILED",
        name="reportgenerationstatus",
    )
    event_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "report_period_summaries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("granularity", period_enum, nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("department_id", sa.String(length=255), nullable=True),
        sa.Column("brigade_id", sa.UUID(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("report_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "summary_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "delta_metrics",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["brigade_id"], ["brigades.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "granularity",
            "period_start",
            "period_end",
            "department_id",
            "brigade_id",
            "author_id",
            name="uq_report_summary_scope",
        ),
    )
    op.create_index(
        op.f("ix_report_period_summaries_granularity"),
        "report_period_summaries",
        ["granularity"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_period_summaries_period_start"),
        "report_period_summaries",
        ["period_start"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_period_summaries_period_end"),
        "report_period_summaries",
        ["period_end"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_period_summaries_department_id"),
        "report_period_summaries",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_period_summaries_brigade_id"),
        "report_period_summaries",
        ["brigade_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_period_summaries_author_id"),
        "report_period_summaries",
        ["author_id"],
        unique=False,
    )

    op.create_table(
        "report_generation_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("report_id", sa.UUID(), nullable=True),
        sa.Column("check_instance_id", sa.UUID(), nullable=True),
        sa.Column("event_type", event_type_enum, nullable=False),
        sa.Column("status", event_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("triggered_by", sa.String(length=128), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["check_instance_id"], ["check_instances.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["report_id"], ["reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_report_generation_events_report_id"),
        "report_generation_events",
        ["report_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_generation_events_check_instance_id"),
        "report_generation_events",
        ["check_instance_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_generation_events_event_type"),
        "report_generation_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_report_generation_events_status"),
        "report_generation_events",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    # Drop report generation events
    op.drop_index(op.f("ix_report_generation_events_status"), table_name="report_generation_events")
    op.drop_index(op.f("ix_report_generation_events_event_type"), table_name="report_generation_events")
    op.drop_index(op.f("ix_report_generation_events_check_instance_id"), table_name="report_generation_events")
    op.drop_index(op.f("ix_report_generation_events_report_id"), table_name="report_generation_events")
    op.drop_table("report_generation_events")

    # Drop report period summaries
    op.drop_index(op.f("ix_report_period_summaries_author_id"), table_name="report_period_summaries")
    op.drop_index(op.f("ix_report_period_summaries_brigade_id"), table_name="report_period_summaries")
    op.drop_index(op.f("ix_report_period_summaries_department_id"), table_name="report_period_summaries")
    op.drop_index(op.f("ix_report_period_summaries_period_end"), table_name="report_period_summaries")
    op.drop_index(op.f("ix_report_period_summaries_period_start"), table_name="report_period_summaries")
    op.drop_index(op.f("ix_report_period_summaries_granularity"), table_name="report_period_summaries")
    op.drop_table("report_period_summaries")

    # Drop enums for new tables
    event_status_enum = postgresql.ENUM(
        "PENDING",
        "RUNNING",
        "SUCCESS",
        "FAILED",
        name="reportgenerationstatus",
    )
    event_type_enum = postgresql.ENUM("manual", "scheduled", "retry", "alert", name="reportgenerationeventtype")
    period_enum = postgresql.ENUM("day", "week", "month", name="periodsummarygranularity")

    bind = op.get_bind()
    event_status_enum.drop(bind, checkfirst=True)
    event_type_enum.drop(bind, checkfirst=True)
    period_enum.drop(bind, checkfirst=True)

    # Revert checklist template columns
    op.drop_index(op.f("ix_checklist_templates_name_slug"), table_name="checklist_templates")
    op.drop_column("checklist_templates", "is_deleted")
    op.drop_column("checklist_templates", "name_slug")

    # Revert brigade score columns
    op.drop_column("brigade_daily_scores", "formula_version")
    op.drop_column("brigade_daily_scores", "overall_score")

    # Revert reports table changes
    op.drop_constraint("fk_reports_author_id", "reports", type_="foreignkey")
    op.drop_index(op.f("ix_reports_author_id"), table_name="reports")
    op.drop_column("reports", "author_id")
    op.drop_column("reports", "metadata")

    op.execute("UPDATE reports SET format = 'json'")
    op.execute("ALTER TABLE reports ALTER COLUMN format TYPE text")
    op.execute("DROP TYPE IF EXISTS reportformatxlsx")
    legacy_enum = postgresql.ENUM("pdf", "html", "json", name="reportformat")
    legacy_enum.create(bind, checkfirst=True)
    op.execute("ALTER TABLE reports ALTER COLUMN format TYPE reportformat USING format::reportformat")

