"""Add brigade domain models and relationships.

Revision ID: add_brigades_20251113
Revises: b545057304d5
Create Date: 2025-11-13 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "add_brigades_20251113"
down_revision = "b545057304d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply brigade schema additions."""
    bind = op.get_bind()
    inspector = inspect(bind)

    if "brigades" not in inspector.get_table_names():
        op.create_table(
            "brigades",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.String(length=1024), nullable=True),
            sa.Column("leader_id", sa.UUID(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "profile",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                server_default=sa.text("'{}'::jsonb"),
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
            sa.ForeignKeyConstraint(["leader_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_brigades_id"), "brigades", ["id"], unique=False)
        op.create_index(op.f("ix_brigades_name"), "brigades", ["name"], unique=True)
        op.create_index(op.f("ix_brigades_leader_id"), "brigades", ["leader_id"], unique=False)

    if "brigade_members" not in inspector.get_table_names():
        op.create_table(
            "brigade_members",
            sa.Column("brigade_id", sa.UUID(), nullable=False),
            sa.Column("user_id", sa.UUID(), nullable=False),
            sa.Column(
                "joined_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.ForeignKeyConstraint(["brigade_id"], ["brigades.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("brigade_id", "user_id"),
        )

    if "brigade_daily_scores" not in inspector.get_table_names():
        op.create_table(
            "brigade_daily_scores",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("brigade_id", sa.UUID(), nullable=False),
            sa.Column("score_date", sa.Date(), nullable=False),
            sa.Column("score", sa.Numeric(10, 2), nullable=False, server_default=sa.text("0")),
            sa.Column(
                "details",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                server_default=sa.text("'{}'::jsonb"),
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
            sa.ForeignKeyConstraint(["brigade_id"], ["brigades.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("brigade_id", "score_date", name="uq_brigade_score_day"),
        )
        op.create_index(
            op.f("ix_brigade_daily_scores_id"),
            "brigade_daily_scores",
            ["id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_brigade_daily_scores_brigade_id"),
            "brigade_daily_scores",
            ["brigade_id"],
            unique=False,
        )
        op.create_index(
            op.f("ix_brigade_daily_scores_score_date"),
            "brigade_daily_scores",
            ["score_date"],
            unique=False,
        )

    columns = [col["name"] for col in inspector.get_columns("check_instances")]
    if "brigade_id" not in columns:
        op.add_column(
            "check_instances",
            sa.Column("brigade_id", sa.UUID(), nullable=True),
        )
        op.create_index(
            op.f("ix_check_instances_brigade_id"),
            "check_instances",
            ["brigade_id"],
            unique=False,
        )
        op.create_foreign_key(
            "fk_check_instances_brigade",
            "check_instances",
            "brigades",
            ["brigade_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Revert brigade schema additions."""
    op.drop_constraint("fk_check_instances_brigade", "check_instances", type_="foreignkey")
    op.drop_index(op.f("ix_check_instances_brigade_id"), table_name="check_instances")
    op.drop_column("check_instances", "brigade_id")

    op.drop_index(op.f("ix_brigade_daily_scores_score_date"), table_name="brigade_daily_scores")
    op.drop_index(op.f("ix_brigade_daily_scores_brigade_id"), table_name="brigade_daily_scores")
    op.drop_index(op.f("ix_brigade_daily_scores_id"), table_name="brigade_daily_scores")
    op.drop_table("brigade_daily_scores")

    op.drop_table("brigade_members")

    op.drop_index(op.f("ix_brigades_leader_id"), table_name="brigades")
    op.drop_index(op.f("ix_brigades_name"), table_name="brigades")
    op.drop_index(op.f("ix_brigades_id"), table_name="brigades")
    op.drop_table("brigades")

