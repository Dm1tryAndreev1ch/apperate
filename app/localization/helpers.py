"""Localization helper functions."""
from __future__ import annotations

from typing import Optional
from fastapi import Request

from app.localization.translations import TRANSLATIONS


def get_locale_from_request(request: Optional[Request] = None, default: str = "en") -> str:
    """Extract locale from request Accept-Language header or return default."""
    if request is None:
        return default
    
    accept_language = request.headers.get("Accept-Language", "")
    if not accept_language:
        return default
    
    # Parse Accept-Language header (e.g., "en-US,en;q=0.9,ru;q=0.8")
    # We'll take the first language code
    languages = accept_language.split(",")
    if languages:
        first_lang = languages[0].split(";")[0].strip().lower()
        # Map to supported locales
        if first_lang.startswith("ru"):
            return "ru"
        elif first_lang.startswith("zh"):
            return "zh"
        elif first_lang.startswith("en"):
            return "en"
    
    return default


def get_translation(key: str, locale: str = "en", **kwargs) -> str:
    """Get translated message for a key, with optional formatting."""
    translations = TRANSLATIONS.get(locale.lower(), TRANSLATIONS.get("en", {}))
    message = translations.get(key, key)
    
    # Format message with kwargs if provided
    if kwargs:
        try:
            message = message.format(**kwargs)
        except (KeyError, ValueError):
            # If formatting fails, return message as-is
            pass
    
    return message


def t(key: str, locale: str = "en", **kwargs) -> str:
    """Short alias for get_translation."""
    return get_translation(key, locale, **kwargs)


