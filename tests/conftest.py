"""Pytest configuration and fixtures."""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, get_db
from app.models.user import User, Role
from app.models.checklist import ChecklistTemplate, TemplateStatus
from app.services.auth_service import AuthService
import uuid


# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

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


@pytest.fixture(scope="function")
async def db_session():
    """Create a test database session."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestSessionLocal() as session:
        yield session
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client."""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash=AuthService.hash_password("testpassword"),
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_admin_role(db_session: AsyncSession):
    """Create admin role."""
    role = Role(
        id=uuid.uuid4(),
        name="admin",
        permissions=["checklist.create", "template.create", "user.view"],
        description="Admin role",
    )
    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)
    return role


@pytest.fixture
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
    response = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "testpassword"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

