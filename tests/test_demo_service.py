"""Tests for demo data generation and reset utilities."""
import threading

import pytest
from sqlalchemy import func, select

from app.core.security import ROLE_PERMISSIONS
from app.models.brigade import Brigade, BrigadeDailyScore
from app.models.checklist import CheckInstance, ChecklistTemplate
from app.models.report import Report
from app.models.user import Role, User
from app.services import demo_service


@pytest.fixture
def mock_storage(monkeypatch):
    """Replace storage service methods with in-memory stubs."""
    stored_objects = {}
    lock = threading.Lock()

    def file_exists(key: str) -> bool:
        with lock:
            return key in stored_objects

    def upload_fileobj(file_obj, key: str, content_type: str | None = None) -> bool:
        data = file_obj.read()
        with lock:
            stored_objects[key] = {
                "content_type": content_type,
                "size": len(data),
            }
        return True

    monkeypatch.setattr(demo_service.storage_service, "file_exists", file_exists)
    monkeypatch.setattr(demo_service.storage_service, "upload_fileobj", upload_fileobj)
    return stored_objects


@pytest.mark.asyncio
async def test_generate_demo_data_creates_entities(db_session, test_user, mock_storage):
    """Ensure demo data generation seeds the expected entities once."""
    payload = await demo_service.generate_demo_data(db_session, test_user)

    expected_reports = sum(len(item["report_formats"]) for item in demo_service.DEMO_CHECKS)

    assert payload["status"] == "created"
    assert payload["detail"]
    assert not payload["already_populated"]
    assert payload["created_users"] == len(demo_service.DEMO_USERS)
    assert payload["created_brigades"] == len(demo_service.DEMO_BRIGADES)
    assert payload["created_templates"] == len(demo_service.DEMO_TEMPLATES)
    assert payload["created_checks"] == len(demo_service.DEMO_CHECKS)
    assert payload["created_reports"] == expected_reports
    assert payload["created_scores"] == len(demo_service.DEMO_BRIGADES) * 5

    # Verify data persisted in the database.
    total_users = await db_session.scalar(select(func.count(User.id)))
    assert total_users == payload["created_users"] + 1  # includes pre-created test user

    brigade_count = await db_session.scalar(select(func.count(Brigade.id)))
    assert brigade_count == payload["created_brigades"]

    template_count = await db_session.scalar(select(func.count(ChecklistTemplate.id)))
    assert template_count == payload["created_templates"]

    check_count = await db_session.scalar(select(func.count(CheckInstance.id)))
    assert check_count == payload["created_checks"]

    report_count = await db_session.scalar(select(func.count(Report.id)))
    assert report_count == payload["created_reports"]

    score_count = await db_session.scalar(select(func.count(BrigadeDailyScore.id)))
    assert score_count == payload["created_scores"]

    # Ensure placeholder files were created for each generated report.
    assert len(mock_storage) == payload["created_reports"]

    # Second invocation should detect pre-populated data and skip mutations.
    second_payload = await demo_service.generate_demo_data(db_session, test_user)
    assert second_payload["status"] == "skipped"
    assert second_payload["already_populated"]
    assert all(
        second_payload[key] == 0
        for key in (
            "created_users",
            "created_brigades",
            "created_templates",
            "created_checks",
            "created_reports",
            "created_scores",
        )
    )
    # No extra storage writes should be recorded on subsequent runs.
    assert len(mock_storage) == payload["created_reports"]


@pytest.mark.asyncio
async def test_reset_project_to_clean_state_recreates_admin(db_session, test_user, mock_storage):
    """Resetting the project should wipe data and create the default admin."""
    # Seed demo data first to ensure there is something to reset.
    await demo_service.generate_demo_data(db_session, test_user)

    payload = await demo_service.reset_project_to_clean_state(db_session)

    assert payload["status"] == "reset"
    assert payload["records_removed"] > 0
    assert payload["roles_seeded"] == len(ROLE_PERMISSIONS)
    assert payload["admin_email"] == demo_service.DEFAULT_ADMIN_EMAIL
    assert payload["admin_password"] == demo_service.DEFAULT_ADMIN_PASSWORD

    # Only the default admin should remain.
    total_users = await db_session.scalar(select(func.count(User.id)))
    assert total_users == 1

    admin = await db_session.scalar(
        select(User).where(User.email == demo_service.DEFAULT_ADMIN_EMAIL)
    )
    assert admin is not None

    # All roles are recreated from the permissions map.
    role_count = await db_session.scalar(select(func.count(Role.id)))
    assert role_count == len(ROLE_PERMISSIONS)

    # Ensure operational data tables are cleared.
    assert await db_session.scalar(select(func.count(Brigade.id))) == 0
    assert await db_session.scalar(select(func.count(CheckInstance.id))) == 0
    assert await db_session.scalar(select(func.count(Report.id))) == 0
    assert await db_session.scalar(select(func.count(BrigadeDailyScore.id))) == 0

