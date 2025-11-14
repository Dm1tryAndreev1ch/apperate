"""Tests for checklist CRUD service."""
import pytest
from uuid import uuid4

from app.models.checklist import ChecklistTemplate, TemplateStatus
from app.schemas.checklist import ChecklistTemplateCreate, ChecklistTemplateUpdate
from app.services.checklist_crud_service import checklist_crud_service


@pytest.mark.asyncio
async def test_create_template(db_session, test_user):
    """Test creating a template via CRUD service."""
    template_data = ChecklistTemplateCreate(
        name="New Template",
        description="Test description",
        schema={
            "sections": [{
                "name": "Section 1",
                "questions": [{
                    "id": "q1",
                    "type": "boolean",
                    "text": "Is OK?",
                    "required": True,
                }]
            }]
        },
    )
    
    template = await checklist_crud_service.create_template(
        db_session,
        template_data=template_data,
        created_by=test_user,
    )
    
    assert template is not None
    assert template.name == "New Template"
    assert template.name_slug is not None
    assert len(template.name_slug) > 0
    assert template.version == 1
    assert template.status == TemplateStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_template_by_slug(db_session, test_user):
    """Test getting template by slug."""
    template = ChecklistTemplate(
        id=uuid4(),
        name="Test Template",
        name_slug="test-template",
        schema={"sections": []},
        version=1,
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(template)
    await db_session.commit()
    
    found = await checklist_crud_service.get_template_by_slug(
        db_session,
        slug="test-template",
    )
    
    assert found is not None
    assert found.id == template.id
    assert found.name_slug == "test-template"


@pytest.mark.asyncio
async def test_update_template(db_session, test_user):
    """Test updating a template."""
    template = ChecklistTemplate(
        id=uuid4(),
        name="Original Name",
        name_slug="original-name",
        schema={"sections": []},
        version=1,
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(template)
    await db_session.commit()
    
    update_data = ChecklistTemplateUpdate(
        name="Updated Name",
        description="Updated description",
    )
    
    updated = await checklist_crud_service.update_template(
        db_session,
        template_obj=template,
        update_data=update_data,
        updated_by=test_user,
    )
    
    assert updated.name == "Updated Name"
    assert updated.description == "Updated description"


@pytest.mark.asyncio
async def test_delete_template_soft(db_session, test_user):
    """Test soft deleting a template."""
    template = ChecklistTemplate(
        id=uuid4(),
        name="To Delete",
        name_slug="to-delete",
        schema={"sections": []},
        version=1,
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(template)
    await db_session.commit()
    
    success = await checklist_crud_service.delete_template(
        db_session,
        template_id=template.id,
        soft_delete=True,
    )
    
    assert success is True
    
    await db_session.refresh(template)
    assert template.is_deleted is True


@pytest.mark.asyncio
async def test_clone_template(db_session, test_user):
    """Test cloning a template."""
    original = ChecklistTemplate(
        id=uuid4(),
        name="Original Template",
        name_slug="original-template",
        schema={"sections": [{"name": "Section 1", "questions": []}]},
        version=1,
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(original)
    await db_session.commit()
    
    cloned = await checklist_crud_service.clone_template(
        db_session,
        template_id=original.id,
        new_name="Cloned Template",
        created_by=test_user,
    )
    
    assert cloned is not None
    assert cloned.name == "Cloned Template"
    assert cloned.id != original.id
    assert cloned.schema == original.schema
    assert cloned.name_slug != original.name_slug

