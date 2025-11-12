"""Templates API endpoints."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import User
from app.core.security import Permission
from app.crud.checklist import template
from app.services.checklist_service import checklist_service
from app.schemas.checklist import (
    ChecklistTemplateCreate,
    ChecklistTemplateUpdate,
    ChecklistTemplateResponse,
    ChecklistTemplateVersionResponse,
)
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("", response_model=List[ChecklistTemplateResponse])
async def list_templates(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all checklist templates."""
    templates = await template.get_multi(db, skip=skip, limit=limit)
    return templates


@router.post("", response_model=ChecklistTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: ChecklistTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TEMPLATE_CREATE)),
):
    """Create a new checklist template."""
    template_dict = template_data.dict()
    template_dict["created_by"] = current_user.id
    new_template = await template.create(db, obj_in=template_data)
    return new_template


@router.get("/{template_id}", response_model=ChecklistTemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a checklist template by ID."""
    template_obj = await template.get(db, id=template_id)
    if not template_obj:
        raise NotFoundError("Template not found")
    return template_obj


@router.put("/{template_id}", response_model=ChecklistTemplateResponse)
async def update_template(
    template_id: UUID,
    template_data: ChecklistTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TEMPLATE_UPDATE)),
):
    """Update a checklist template (creates a new version)."""
    template_obj = await template.get(db, id=template_id)
    if not template_obj:
        raise NotFoundError("Template not found")

    # Create new version if schema is being updated
    if template_data.schema is not None:
        await checklist_service.create_version(
            db,
            template_obj,
            template_data.schema,
            current_user.id,
        )

    # Update other fields
    update_data = template_data.dict(exclude_unset=True, exclude={"schema"})
    if update_data:
        updated_template = await template.update(db, db_obj=template_obj, obj_in=update_data)
        return updated_template

    await db.refresh(template_obj)
    return template_obj


@router.get("/{template_id}/versions", response_model=List[ChecklistTemplateVersionResponse])
async def get_template_versions(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all versions of a template."""
    versions = await template.get_versions(db, template_id=template_id)
    return versions

