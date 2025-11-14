"""Templates API endpoints with full CRUD operations."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import User
from app.models.checklist import TemplateStatus
from app.core.security import Permission
from app.crud.checklist import template
from app.services.checklist_crud_service import checklist_crud_service
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
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    status_filter: Optional[TemplateStatus] = None,
    search: Optional[str] = Query(default=None, description="Search by name or description"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List checklist templates with optional filtering and search."""
    templates = await checklist_crud_service.list_templates(
        db,
        skip=skip,
        limit=limit,
        status=status_filter,
        search=search,
    )
    return templates


@router.post("", response_model=ChecklistTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: ChecklistTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TEMPLATE_CREATE)),
):
    """Create a new checklist template with validation."""
    try:
        new_template = await checklist_crud_service.create_template(
            db,
            template_data=template_data,
            created_by=current_user,
        )
        return new_template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{template_id}", response_model=ChecklistTemplateResponse)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a checklist template by ID."""
    template_obj = await checklist_crud_service.get_template(db, template_id=template_id)
    if not template_obj:
        raise NotFoundError("Template not found")
    return template_obj


@router.get("/slug/{slug}", response_model=ChecklistTemplateResponse)
async def get_template_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a checklist template by slug."""
    template_obj = await checklist_crud_service.get_template_by_slug(db, slug=slug)
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
    """Update a checklist template (creates a new version if schema changed)."""
    template_obj = await checklist_crud_service.get_template(db, template_id=template_id)
    if not template_obj:
        raise NotFoundError("Template not found")

    try:
        updated_template = await checklist_crud_service.update_template(
            db,
            template_obj=template_obj,
            update_data=template_data,
            updated_by=current_user,
        )
        return updated_template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    soft_delete: bool = Query(default=True, description="Soft delete (archive) or hard delete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TEMPLATE_DELETE)),
):
    """Delete a checklist template (soft delete by default)."""
    success = await checklist_crud_service.delete_template(
        db,
        template_id=template_id,
        soft_delete=soft_delete,
    )
    if not success:
        raise NotFoundError("Template not found")


@router.post("/{template_id}/clone", response_model=ChecklistTemplateResponse, status_code=status.HTTP_201_CREATED)
async def clone_template(
    template_id: UUID,
    new_name: str = Query(..., description="Name for the cloned template"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TEMPLATE_CREATE)),
):
    """Clone an existing template with a new name."""
    try:
        cloned_template = await checklist_crud_service.clone_template(
            db,
            template_id=template_id,
            new_name=new_name,
            created_by=current_user,
        )
        return cloned_template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("/{template_id}/versions", response_model=List[ChecklistTemplateVersionResponse])
async def get_template_versions(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all versions of a template."""
    versions = await checklist_crud_service.get_template_versions(db, template_id=template_id)
    return versions


@router.post("/{template_id}/versions/{version}/restore", response_model=ChecklistTemplateResponse)
async def restore_template_version(
    template_id: UUID,
    version: int = Path(..., ge=1, description="Version number to restore"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TEMPLATE_UPDATE)),
):
    """Restore a template to a specific version (creates a new version with restored schema)."""
    try:
        restored_template = await checklist_crud_service.restore_template_version(
            db,
            template_id=template_id,
            version=version,
            restored_by=current_user,
        )
        return restored_template
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
