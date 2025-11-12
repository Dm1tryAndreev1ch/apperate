"""RBAC permission helpers."""
from typing import List
from app.models.user import User
from app.core.security import Permission


def has_permission(user: User, permission: Permission) -> bool:
    """Check if user has a specific permission."""
    if not user.is_active:
        return False

    # Get all permissions from user's roles
    user_permissions = set()
    for role in user.roles:
        if role.permissions:
            user_permissions.update(role.permissions)

    return permission.value in user_permissions


def has_any_permission(user: User, permissions: List[Permission]) -> bool:
    """Check if user has any of the specified permissions."""
    return any(has_permission(user, perm) for perm in permissions)


def has_all_permissions(user: User, permissions: List[Permission]) -> bool:
    """Check if user has all of the specified permissions."""
    return all(has_permission(user, perm) for perm in permissions)


def get_user_permissions(user: User) -> List[str]:
    """Get all permissions for a user."""
    permissions = set()
    for role in user.roles:
        if role.permissions:
            permissions.update(role.permissions)
    return list(permissions)

