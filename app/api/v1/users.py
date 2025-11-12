"""Users API endpoints (Admin)."""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import User
from app.core.security import Permission
from app.crud.user import user
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.exceptions import NotFoundError, ConflictError

router = APIRouter()


@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_VIEW)),
):
    """List all users."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .offset(skip)
        .limit(limit)
    )
    users = result.scalars().all()
    return users


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_CREATE)),
):
    """Create a new user."""
    # Check if email already exists
    existing = await user.get_by_email(db, email=user_data.email)
    if existing:
        raise ConflictError("User with this email already exists")

    new_user = await user.create(db, obj_in=user_data)
    return await user.get_with_roles(db, id=new_user.id)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_VIEW)),
):
    """Get a user by ID."""
    user_obj = await user.get_with_roles(db, id=user_id)
    if not user_obj:
        raise NotFoundError("User not found")
    return user_obj


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_UPDATE)),
):
    """Update a user."""
    user_obj = await user.get_with_roles(db, id=user_id)
    if not user_obj:
        raise NotFoundError("User not found")

    # Check email uniqueness if email is being updated
    if user_data.email and user_data.email != user_obj.email:
        existing = await user.get_by_email(db, email=user_data.email)
        if existing:
            raise ConflictError("User with this email already exists")

    updated_user = await user.update(db, db_obj=user_obj, obj_in=user_data)
    return await user.get_with_roles(db, id=updated_user.id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.USER_DELETE)),
):
    """Delete a user."""
    user_obj = await user.get(db, id=user_id)
    if not user_obj:
        raise NotFoundError("User not found")
    await user.remove(db, id=user_id)

