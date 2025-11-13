"""Meta endpoints for localization and configuration."""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_active_user
from app.localization.translations import TRANSLATIONS, get_available_locales
from app.models.user import User

router = APIRouter()


@router.get("/locales", response_model=Dict[str, str])
async def available_locales(
    current_user: User = Depends(get_current_active_user),
):
    """Return list of supported locales."""
    return get_available_locales()


@router.get("/translations/{locale}", response_model=Dict[str, str])
async def translations(
    locale: str,
    current_user: User = Depends(get_current_active_user),
):
    """Return translation bundle for locale."""
    bundle = TRANSLATIONS.get(locale.lower())
    if not bundle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Locale '{locale}' not supported",
        )
    return bundle



