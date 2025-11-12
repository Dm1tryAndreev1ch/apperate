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
        # Check if admin role exists
        result = await db.execute(select(Role).where(Role.name == "admin"))
        admin_role = result.scalar_one_or_none()

        if not admin_role:
            # Create admin role
            admin_role = Role(
                name="admin",
                permissions=[p.value for p in ROLE_PERMISSIONS["admin"]],
                description="Administrator with full access",
            )
            db.add(admin_role)
            await db.commit()
            await db.refresh(admin_role)
            print("✓ Admin role created")
        else:
            print("✓ Admin role already exists")

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
            admin_user.roles = [admin_role]
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

