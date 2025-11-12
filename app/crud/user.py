"""User CRUD operations."""
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.crud.base import CRUDBase
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth_service import AuthService


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD operations for User."""

    async def get_by_email(self, db: AsyncSession, *, email: str) -> Optional[User]:
        """Get user by email."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_with_roles(self, db: AsyncSession, *, id: UUID) -> Optional[User]:
        """Get user with roles loaded."""
        result = await db.execute(
            select(User)
            .where(User.id == id)
            .options(selectinload(User.roles))
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, *, obj_in: UserCreate) -> User:
        """Create a new user with roles."""
        # Hash password
        password_hash = AuthService.hash_password(obj_in.password)

        # Create user
        user_data = obj_in.dict(exclude={"password", "role_ids"})
        user_data["password_hash"] = password_hash
        db_obj = User(**user_data)

        # Assign roles if provided
        if obj_in.role_ids:
            result = await db.execute(
                select(Role).where(Role.id.in_(obj_in.role_ids))
            )
            roles = result.scalars().all()
            db_obj.roles = roles

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await db.refresh(db_obj, ["roles"])
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: User,
        obj_in: UserUpdate,
    ) -> User:
        """Update user."""
        update_data = obj_in.dict(exclude_unset=True, exclude={"password", "role_ids"})

        # Update password if provided
        if obj_in.password:
            update_data["password_hash"] = AuthService.hash_password(obj_in.password)

        # Update roles if provided
        if obj_in.role_ids is not None:
            result = await db.execute(
                select(Role).where(Role.id.in_(obj_in.role_ids))
            )
            roles = result.scalars().all()
            db_obj.roles = roles

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        await db.refresh(db_obj, ["roles"])
        return db_obj


class CRUDRole(CRUDBase[Role, dict, dict]):
    """CRUD operations for Role."""

    async def get_by_name(self, db: AsyncSession, *, name: str) -> Optional[Role]:
        """Get role by name."""
        result = await db.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()


user = CRUDUser(User)
role = CRUDRole(Role)

