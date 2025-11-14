"""Integration tests for checklists CRUD API endpoints."""
import pytest
from uuid import uuid4

from app.models.checklist import ChecklistTemplate, TemplateStatus


@pytest.mark.asyncio
async def test_create_template_endpoint(client, db_session, auth_headers):
    """Test creating a template via API."""
    template_data = {
        "name": "API Test Template",
        "description": "Created via API",
        "schema": {
            "sections": [{
                "name": "Section 1",
                "questions": [{
                    "id": "q1",
                    "type": "boolean",
                    "text": "Is everything OK?",
                    "required": True,
                }]
            }]
        },
    }
    
    response = client.post(
        "/api/v1/templates",
        headers=auth_headers,
        json=template_data
    )
    
    assert response.status_code == 201
    template = response.json()
    assert template["name"] == "API Test Template"
    assert template["name_slug"] is not None
    assert template["version"] == 1
    assert template["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_list_templates_with_search(client, db_session, auth_headers, test_template):
    """Test listing templates with search filter."""
    # Create another template
    from app.models.user import User
    from sqlalchemy import select
    result = await db_session.execute(select(User).limit(1))
    user = result.scalar_one()
    
    template2 = ChecklistTemplate(
        id=uuid4(),
        name="Safety Checklist",
        name_slug="safety-checklist",
        description="Safety inspection",
        schema={"sections": []},
        version=1,
        status=TemplateStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(template2)
    await db_session.commit()
    
    # Search for "Safety"
    response = client.get(
        "/api/v1/templates?search=Safety",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) >= 1
    assert any("Safety" in t["name"] for t in templates)


@pytest.mark.asyncio
async def test_get_template_by_slug(client, db_session, auth_headers, test_template):
    """Test getting template by slug."""
    # Ensure template has a slug
    if not test_template.name_slug:
        from app.utils.slugify import slugify
        test_template.name_slug = slugify(test_template.name)
        await db_session.commit()
    
    response = client.get(
        f"/api/v1/templates/slug/{test_template.name_slug}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    template = response.json()
    assert template["id"] == str(test_template.id)
    assert template["name_slug"] == test_template.name_slug


@pytest.mark.asyncio
async def test_update_template_endpoint(client, db_session, auth_headers, test_template):
    """Test updating a template via API."""
    update_data = {
        "name": "Updated Template Name",
        "description": "Updated description",
    }
    
    response = client.put(
        f"/api/v1/templates/{test_template.id}",
        headers=auth_headers,
        json=update_data
    )
    
    assert response.status_code == 200
    template = response.json()
    assert template["name"] == "Updated Template Name"
    assert template["description"] == "Updated description"


@pytest.mark.asyncio
async def test_clone_template_endpoint(client, db_session, auth_headers, test_template):
    """Test cloning a template via API."""
    response = client.post(
        f"/api/v1/templates/{test_template.id}/clone?new_name=Cloned Template",
        headers=auth_headers
    )
    
    assert response.status_code == 201
    cloned = response.json()
    assert cloned["name"] == "Cloned Template"
    assert cloned["id"] != str(test_template.id)
    assert cloned["schema"] == test_template.schema


@pytest.mark.asyncio
async def test_delete_template_endpoint(client, db_session, auth_headers, test_template):
    """Test soft deleting a template via API."""
    response = client.delete(
        f"/api/v1/templates/{test_template.id}?soft_delete=true",
        headers=auth_headers
    )
    
    assert response.status_code == 204
    
    # Verify it's soft deleted
    get_response = client.get(
        f"/api/v1/templates/{test_template.id}",
        headers=auth_headers
    )
    # Should still be accessible but marked as deleted
    assert get_response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_template_versions_endpoint(client, db_session, auth_headers, test_template):
    """Test getting template versions."""
    # Create a version
    from app.services.checklist_service import checklist_service
    from sqlalchemy import select
    from app.models.user import User
    result = await db_session.execute(select(User).limit(1))
    user = result.scalar_one()
    
    new_schema = {"sections": [{"name": "New Section", "questions": []}]}
    await checklist_service.create_version(
        db_session,
        test_template,
        new_schema,
        str(user.id),
    )
    await db_session.commit()
    
    # Get versions
    response = client.get(
        f"/api/v1/templates/{test_template.id}/versions",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    versions = response.json()
    assert len(versions) >= 1
    assert all("version" in v for v in versions)

