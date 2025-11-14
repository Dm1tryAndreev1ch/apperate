"""Tests for reset service."""
import pytest
from uuid import uuid4

from app.models.user import User
from app.models.checklist import ChecklistTemplate, TemplateStatus
from app.models.checklist import CheckInstance, CheckStatus
from app.services.reset_service import reset_service
from app.services.bootstrap_service import ensure_default_admin


@pytest.mark.asyncio
async def test_reset_project_clears_data(db_session, test_user):
    """Test that reset project clears all data except admin."""
    # Create some test data
    template = ChecklistTemplate(
        id=uuid4(),
        name="Test Template",
        schema={"sections": []},
        version=1,
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(template)
    
    check = CheckInstance(
        id=uuid4(),
        template_id=template.id,
        template_version=1,
        inspector_id=test_user.id,
        status=CheckStatus.IN_PROGRESS,
        answers={},
    )
    db_session.add(check)
    await db_session.commit()
    
    # Ensure admin exists
    await ensure_default_admin(db_session)
    await db_session.commit()
    
    # Reset project
    result = await reset_service.reset_project(db_session)
    
    assert result is not None
    assert result.get("admin_user_preserved", False)
    
    # Verify admin still exists
    from sqlalchemy import select
    from app.models.user import User
    result_query = await db_session.execute(
        select(User).where(User.email == "admin@example.com")
    )
    admin = result_query.scalar_one_or_none()
    assert admin is not None


@pytest.mark.asyncio
async def test_verify_reset(db_session):
    """Test reset verification."""
    # Ensure admin exists
    await ensure_default_admin(db_session)
    await db_session.commit()
    
    verification = await reset_service.verify_reset(db_session)
    
    assert verification is not None
    assert "admin_exists" in verification
    assert verification["admin_exists"] is True

