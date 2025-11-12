"""Roles API endpoints (Admin)."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import User
from app.core.security import Permission
from app.crud.user import role
from app.schemas.user import RoleCreate, RoleResponse
from app.core.exceptions import NotFoundError, ConflictError

router = APIRouter()


@router.get("", response_model=List[RoleResponse])
async def list_roles(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ROLE_VIEW)),
):
    """List all roles."""
    roles = await role.get_multi(db, skip=skip, limit=limit)
    return roles


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ROLE_CREATE)),
):
    """Create a new role."""
    # Check if name already exists
    existing = await role.get_by_name(db, name=role_data.name)
    if existing:
        raise ConflictError("Role with this name already exists")

    new_role = await role.create(db, obj_in=role_data.dict())
    return new_role


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ROLE_VIEW)),
):
    """Get a role by ID."""
    role_obj = await role.get(db, id=role_id)
    if not role_obj:
        raise NotFoundError("Role not found")
    return role_obj


@router.put("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: UUID,
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ROLE_UPDATE)),
):
    """Update a role."""
    role_obj = await role.get(db, id=role_id)
    if not role_obj:
        raise NotFoundError("Role not found")

    # Check name uniqueness if name is being updated
    if role_data.name != role_obj.name:
        existing = await role.get_by_name(db, name=role_data.name)
        if existing:
            raise ConflictError("Role with this name already exists")

    updated_role = await role.update(db, db_obj=role_obj, obj_in=role_data.dict())
    return updated_role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.ROLE_DELETE)),
):
    """Delete a role."""
    role_obj = await role.get(db, id=role_id)
    if not role_obj:
        raise NotFoundError("Role not found")
    await role.remove(db, id=role_id)

