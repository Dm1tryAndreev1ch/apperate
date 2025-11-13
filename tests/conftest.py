"""Pytest configuration and fixtures."""
import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

TEST_DB_PATH = Path("test_app.db")
if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink()

TEST_DATABASE_URL = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("BITRIX_MODE", "stub")
os.environ.setdefault("ENCRYPTION_SECRET", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")

from app.main import app  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.models.user import User, Role  # noqa: E402
from app.models.checklist import ChecklistTemplate, TemplateStatus  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402
from app.utils.security import create_access_token  # noqa: E402
from app.core.security import ROLE_PERMISSIONS  # noqa: E402


# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def client(db_session: AsyncSession):
    """Create a test client overriding database dependency."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_admin_role(db_session: AsyncSession):
    """Create admin role."""
    role = Role(
        id=uuid.uuid4(),
        name="admin",
        permissions=[perm.value for perm in ROLE_PERMISSIONS["admin"]],
        description="Admin role",
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, test_admin_role: Role):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash=AuthService.hash_password("testpassword"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    user.roles.append(test_admin_role)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_template(db_session: AsyncSession, test_user: User):
    """Create a test checklist template."""
    template = ChecklistTemplate(
        id=uuid.uuid4(),
        name="Test Template",
        description="Test description",
        version=1,
        schema={
            "sections": [
                {
                    "name": "Section 1",
                    "questions": [
                        {
                            "id": "q1",
                            "type": "boolean",
                            "text": "Is everything OK?",
                            "required": True,
                            "meta": {"critical": True, "requires_ok": True},
                        }
                    ],
                }
            ]
        },
        status=TemplateStatus.ACTIVE,
        created_by=test_user.id,
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers."""
    token = create_access_token(
        {"sub": str(test_user.id), "email": test_user.email}
    )
    return {"Authorization": f"Bearer {token}"}

