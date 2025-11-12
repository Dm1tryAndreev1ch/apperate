"""Authentication service."""
from datetime import timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.utils.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
from app.config import settings
from app.core.exceptions import UnauthorizedError


class AuthService:
    """Authentication service."""

    @staticmethod
    async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate a user by email and password."""
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            return None

        return user

    @staticmethod
    async def create_tokens(user: User) -> dict:
        """Create access and refresh tokens for a user."""
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires,
        )
        refresh_token = create_refresh_token(data={"sub": str(user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }

    @staticmethod
    async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict:
        """Refresh access token using refresh token."""
        try:
            payload = decode_token(refresh_token)
            token_type = payload.get("type")

            if token_type != "refresh":
                raise UnauthorizedError("Invalid token type")

            user_id = payload.get("sub")
            if not user_id:
                raise UnauthorizedError("Invalid token")

            # Get user from database
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if not user or not user.is_active:
                raise UnauthorizedError("User not found or inactive")

            # Create new access token
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": str(user.id), "email": user.email},
                expires_delta=access_token_expires,
            )

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            }
        except ValueError:
            raise UnauthorizedError("Invalid refresh token")

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password."""
        return get_password_hash(password)

