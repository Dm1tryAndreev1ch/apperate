"""User schemas."""
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr
from datetime import datetime
from app.schemas.brigade import BrigadeSummary


class RoleBase(BaseModel):
    """Base role schema."""

    name: str
    permissions: List[str]
    description: Optional[str] = None


class RoleCreate(RoleBase):
    """Role creation schema."""

    pass


class RoleResponse(RoleBase):
    """Role response schema."""

    id: UUID
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    full_name: str
    is_active: bool = True


class UserCreate(UserBase):
    """User creation schema."""

    password: str
    role_ids: Optional[List[UUID]] = None


class UserUpdate(BaseModel):
    """User update schema."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[UUID]] = None
    password: Optional[str] = None


class UserResponse(UserBase):
    """User response schema."""

    id: UUID
    roles: List[RoleResponse] = []
    brigades: List[BrigadeSummary] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

