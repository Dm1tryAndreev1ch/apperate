"""Reset service for safely clearing project data while preserving admin user."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.bootstrap_service import DEFAULT_ADMIN_EMAIL, ensure_default_admin, ensure_roles


class ResetService:
    """Service for safely resetting project data."""

    # Tables to preserve (admin user and roles)
    PRESERVE_TABLES = {
        "users",
        "roles",
        "user_role_association",
        "alembic_version",
    }

    # Tables to truncate (all data tables)
    TRUNCATE_TABLES = [
        "report_generation_events",
        "reports",
        "check_instances",
        "checklist_template_versions",
        "checklist_templates",
        "brigade_daily_scores",
        "brigade_members",
        "brigades",
        "schedules",
        "webhook_subscriptions",
        "audit_logs",
        "bitrix_call_logs",
        "data_calculation_runs",
        "data_quality_issues",
        "remark_entries",
        "equipment_register_entries",
        "daily_checklist_metrics",
        "department_monthly_summaries",
        "equipment_status_snapshots",
        "department_historical_comparisons",
        "task_local",
    ]

    @staticmethod
    async def reset_project(db: AsyncSession) -> Dict[str, Any]:
        """Reset project by clearing all data except admin user and roles."""
        results = {
            "tables_truncated": [],
            "tables_preserved": [],
            "admin_user_preserved": False,
            "errors": [],
        }

        try:
            # Step 1: Disable foreign key checks (PostgreSQL)
            await db.execute(text("SET session_replication_role = 'replica'"))

            # Step 2: Truncate all data tables
            for table_name in ResetService.TRUNCATE_TABLES:
                try:
                    # Use CASCADE to handle foreign keys
                    await db.execute(text(f'TRUNCATE TABLE "{table_name}" CASCADE'))
                    results["tables_truncated"].append(table_name)
                except Exception as e:
                    results["errors"].append(f"Failed to truncate {table_name}: {str(e)}")

            # Step 3: Clean up user_role_association except for admin
            try:
                await db.execute(
                    text(
                        """
                        DELETE FROM user_role_association
                        WHERE user_id NOT IN (
                            SELECT id FROM users WHERE email = :admin_email
                        )
                        """
                    ),
                    {"admin_email": DEFAULT_ADMIN_EMAIL},
                )
            except Exception as e:
                results["errors"].append(f"Failed to clean user_role_association: {str(e)}")

            # Step 4: Delete all users except admin
            try:
                await db.execute(
                    text("DELETE FROM users WHERE email != :admin_email"),
                    {"admin_email": DEFAULT_ADMIN_EMAIL},
                )
            except Exception as e:
                results["errors"].append(f"Failed to clean users: {str(e)}")

            # Step 5: Re-enable foreign key checks
            await db.execute(text("SET session_replication_role = 'origin'"))

            # Step 6: Ensure admin user exists with proper roles
            role_map = await ensure_roles(db, role_names={"admin"})
            admin_user = await ensure_default_admin(db, role_map=role_map)

            results["admin_user_preserved"] = True
            results["admin_email"] = admin_user.email

            # Step 7: Preserve roles table (already done via ensure_roles)
            results["tables_preserved"] = list(ResetService.PRESERVE_TABLES)

            await db.commit()

            return results

        except Exception as e:
            await db.rollback()
            results["errors"].append(f"Reset failed: {str(e)}")
            raise

    @staticmethod
    async def verify_reset(db: AsyncSession) -> Dict[str, Any]:
        """Verify that reset was successful and admin user can log in."""
        verification = {
            "admin_user_exists": False,
            "admin_has_role": False,
            "data_tables_empty": {},
            "errors": [],
        }

        try:
            # Check admin user
            result = await db.execute(
                text("SELECT id, email FROM users WHERE email = :admin_email"),
                {"admin_email": DEFAULT_ADMIN_EMAIL},
            )
            admin_row = result.fetchone()
            if admin_row:
                verification["admin_user_exists"] = True
                admin_id = admin_row[0]

                # Check admin role
                role_result = await db.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM user_role_association ura
                        JOIN roles r ON ura.role_id = r.id
                        WHERE ura.user_id = :admin_id AND r.name = 'admin'
                        """
                    ),
                    {"admin_id": admin_id},
                )
                role_count = role_result.scalar_one_or_none()
                verification["admin_has_role"] = role_count > 0

            # Check data tables are empty
            for table_name in ResetService.TRUNCATE_TABLES[:5]:  # Check first 5 as sample
                try:
                    count_result = await db.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                    count = count_result.scalar_one_or_none()
                    verification["data_tables_empty"][table_name] = count == 0
                except Exception as e:
                    verification["errors"].append(f"Failed to check {table_name}: {str(e)}")

            return verification

        except Exception as e:
            verification["errors"].append(f"Verification failed: {str(e)}")
            return verification


reset_service = ResetService()

