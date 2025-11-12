"""Tests for authentication."""
import pytest
from app.services.auth_service import AuthService
from app.models.user import User
from app.utils.security import verify_password, create_access_token, decode_token


def test_password_hashing():
    """Test password hashing and verification."""
    password = "testpassword123"
    hashed = AuthService.hash_password(password)
    
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_jwt_token_creation():
    """Test JWT token creation and decoding."""
    data = {"sub": "user123", "email": "test@example.com"}
    token = create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    
    decoded = decode_token(token)
    assert decoded["sub"] == "user123"
    assert decoded["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_authenticate_user(db_session, test_user):
    """Test user authentication."""
    # Test correct credentials
    user = await AuthService.authenticate_user(
        db_session,
        "test@example.com",
        "testpassword",
    )
    assert user is not None
    assert user.email == "test@example.com"
    
    # Test incorrect password
    user = await AuthService.authenticate_user(
        db_session,
        "test@example.com",
        "wrongpassword",
    )
    assert user is None
    
    # Test non-existent user
    user = await AuthService.authenticate_user(
        db_session,
        "nonexistent@example.com",
        "password",
    )
    assert user is None

