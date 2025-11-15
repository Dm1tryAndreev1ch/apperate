"""Meta endpoints for localization and configuration."""
from __future__ import annotations

from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_active_user
from app.localization.translations import TRANSLATIONS, get_available_locales
from app.localization.helpers import get_translation
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
        # Use default locale for error message
        default_locale = "en"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=get_translation("errors.locale_not_supported", default_locale, locale=locale),
        )
    return bundle



