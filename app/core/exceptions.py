"""Custom exceptions."""
from typing import Optional
from fastapi import HTTPException, status
from app.localization.helpers import get_translation


class NotFoundError(HTTPException):
    """Resource not found exception."""

    def __init__(self, detail: Optional[str] = None, locale: str = "en"):
        if detail is None:
            detail = get_translation("errors.resource_not_found", locale)
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthorizedError(HTTPException):
    """Unauthorized exception."""

    def __init__(self, detail: Optional[str] = None, locale: str = "en"):
        if detail is None:
            detail = get_translation("errors.not_authenticated", locale)
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenError(HTTPException):
    """Forbidden exception."""

    def __init__(self, detail: Optional[str] = None, locale: str = "en"):
        if detail is None:
            detail = get_translation("errors.permission_denied", locale)
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ValidationError(HTTPException):
    """Validation exception."""

    def __init__(self, detail: Optional[str] = None, locale: str = "en"):
        if detail is None:
            detail = get_translation("errors.validation_error", locale)
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class ConflictError(HTTPException):
    """Conflict exception."""

    def __init__(self, detail: Optional[str] = None, locale: str = "en"):
        if detail is None:
            detail = get_translation("errors.resource_conflict", locale)
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

