"""Tests for template creation and versioning."""
import pytest
from uuid import uuid4
from app.models.checklist import ChecklistTemplate, TemplateStatus
from app.services.checklist_service import checklist_service


@pytest.mark.asyncio
async def test_create_template(db_session, test_user):
    """Test creating a checklist template."""
    template_data = {
        "name": "Safety Inspection",
        "description": "Daily safety check",
        "schema": {
            "sections": [
                {
                    "name": "Equipment",
                    "questions": [
                        {
                            "id": "eq1",
                            "type": "boolean",
                            "text": "Equipment is safe",
                            "required": True,
                        }
                    ],
                }
            ]
        },
    }
    
    template = ChecklistTemplate(
        id=uuid4(),
        **template_data,
        version=1,
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    
    assert template.name == "Safety Inspection"
    assert template.version == 1
    assert template.status == TemplateStatus.ACTIVE


@pytest.mark.asyncio
async def test_template_versioning(db_session, test_user):
    """Test template versioning when updating."""
    # Create initial template
    template = ChecklistTemplate(
        id=uuid4(),
        name="Test Template",
        version=1,
        schema={"sections": []},
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    
    original_version = template.version
    original_schema = template.schema.copy()
    
    # Create new version
    new_schema = {"sections": [{"name": "New Section", "questions": []}]}
    version = await checklist_service.create_version(
        db_session,
        template,
        new_schema,
        str(test_user.id),
    )
    
    await db_session.refresh(template)
    
    assert template.version == original_version + 1
    assert version.version == template.version
    assert version.template_id == template.id
    assert version.schema == new_schema
    assert version.diff is not None

