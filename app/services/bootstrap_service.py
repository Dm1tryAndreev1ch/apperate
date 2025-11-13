"""Bootstrap utilities for ensuring core roles and the default admin exist."""
from __future__ import annotations

from typing import Dict, Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ROLE_PERMISSIONS
from app.models.user import Role, User
from app.services.auth_service import AuthService

DEFAULT_ROLE_DESCRIPTIONS = {
    "admin": "Administrator with full access",
    "inspector": "Inspector responsible for performing checks",
    "crew_leader": "Crew leader overseeing brigade performance",
    "viewer": "Read-only access",
}

DEFAULT_ADMIN_EMAIL = "admin@example.com"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_ADMIN_NAME = "Administrator"


async def ensure_roles(
    db: AsyncSession,
    *,
    role_names: Iterable[str],
) -> Dict[str, Role]:
    """Ensure that the given roles exist and return them in a mapping."""
    role_map: Dict[str, Role] = {}
    created = False

    for role_name in role_names:
        result = await db.execute(select(Role).where(Role.name == role_name))
        role_obj = result.scalar_one_or_none()
        if role_obj is None:
            permissions = [
                permission.value
                for permission in ROLE_PERMISSIONS.get(role_name, [])
            ]
            role_obj = Role(
                name=role_name,
                permissions=permissions,
                description=DEFAULT_ROLE_DESCRIPTIONS.get(role_name),
            )
            db.add(role_obj)
            await db.flush()
            created = True

        role_map[role_name] = role_obj

    if created:
        await db.commit()

    return role_map


async def ensure_default_admin(
    db: AsyncSession,
    *,
    role_map: Optional[Dict[str, Role]] = None,
    email: str = DEFAULT_ADMIN_EMAIL,
    password: str = DEFAULT_ADMIN_PASSWORD,
    full_name: str = DEFAULT_ADMIN_NAME,
) -> User:
    """Ensure that the default administrator account exists and return it."""
    if role_map is None or "admin" not in role_map:
        role_map = await ensure_roles(db, role_names={"admin"})

    admin_role = role_map["admin"]

    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.email == email)
    )
    admin_user = result.scalar_one_or_none()
    if admin_user:
        # Ensure admin role assignment is present.
        if admin_role not in admin_user.roles:
            admin_user.roles.append(admin_role)
            await db.commit()
        return admin_user

    admin_user = User(
        email=email,
        password_hash=AuthService.hash_password(password),
        full_name=full_name,
        is_active=True,
    )
    admin_user.roles = [admin_role]
    db.add(admin_user)
    await db.commit()
    await db.refresh(admin_user)
    return admin_user


