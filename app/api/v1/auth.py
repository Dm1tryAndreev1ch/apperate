"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import TokenRequest, TokenResponse, RefreshTokenRequest, RefreshTokenResponse
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

