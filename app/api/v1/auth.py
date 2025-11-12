"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.services.auth_service import AuthService
from app.schemas.auth import TokenRequest, TokenResponse, RefreshTokenRequest, RefreshTokenResponse
from app.schemas.user import UserResponse
from app.core.exceptions import UnauthorizedError

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login endpoint - returns access and refresh tokens.
    
    Supports OAuth2 password flow (form data) where username is the email.
    """
    # OAuth2PasswordRequestForm uses 'username' field, but we use email
    user = await AuthService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise UnauthorizedError("Incorrect email or password")

    tokens = await AuthService.create_tokens(user)
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    try:
        tokens = await AuthService.refresh_access_token(db, request.refresh_token)
        return RefreshTokenResponse(**tokens)
    except UnauthorizedError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get current authenticated user information."""
    return current_user

