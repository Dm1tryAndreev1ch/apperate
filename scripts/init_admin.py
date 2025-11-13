"""Script to create initial admin user and role."""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.user import User, Role
from app.core.security import ROLE_PERMISSIONS
import bcrypt


async def init_admin():
    """Create admin role and user if they don't exist."""
    async with AsyncSessionLocal() as db:
        created_roles = []
        role_cache = {}

        for role_name, permissions in ROLE_PERMISSIONS.items():
            result = await db.execute(select(Role).where(Role.name == role_name))
            role_obj = result.scalar_one_or_none()

            if not role_obj:
                role_obj = Role(
                    name=role_name,
                    permissions=[p.value for p in permissions],
                    description={
                        "admin": "Administrator with full access",
                        "inspector": "Inspector responsible for performing checks",
                        "crew_leader": "Crew leader overseeing brigade performance",
                        "viewer": "Read-only access",
                    }.get(role_name, f"Default role: {role_name}"),
                )
                db.add(role_obj)
                await db.commit()
                await db.refresh(role_obj)
                created_roles.append(role_name)
            else:
                # Ensure permissions stay in sync with definitions
                current_permissions = set(role_obj.permissions or [])
                desired_permissions = {p.value for p in permissions}
                if current_permissions != desired_permissions:
                    role_obj.permissions = list(desired_permissions)
                    db.add(role_obj)
                    await db.commit()
                    await db.refresh(role_obj)
                    print(f"✓ Updated permissions for role '{role_name}'")

            role_cache[role_name] = role_obj

        if created_roles:
            print("✓ Created roles:", ", ".join(created_roles))
        else:
            print("✓ All default roles already exist")

        # Check if admin user exists
        result = await db.execute(select(User).where(User.email == "admin@example.com"))
        admin_user = result.scalar_one_or_none()

        if not admin_user:
            # Create admin user
            # Use bcrypt directly to avoid passlib issues
            password = "admin123"
            password_bytes = password.encode('utf-8')
            password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode('utf-8')
            admin_user = User(
                email="admin@example.com",
                password_hash=password_hash,
                full_name="Administrator",
                is_active=True,
            )
            admin_user.roles = [role_cache["admin"]]
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            print("✓ Admin user created")
            print("\n" + "=" * 50)
            print("Admin credentials:")
            print("  Email: admin@example.com")
            print("  Password: admin123")
            print("=" * 50)
        else:
            print("✓ Admin user already exists")
            print("\nAdmin user email: admin@example.com")
            print("(Password was set during initial creation)")


if __name__ == "__main__":
    asyncio.run(init_admin())

