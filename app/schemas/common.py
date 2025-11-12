"""Common schemas."""
from typing import Optional
from pydantic import BaseModel


class PaginationParams(BaseModel):
    """Pagination parameters."""

    skip: int = 0
    limit: int = 100

    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    """Paginated response."""

    total: int
    skip: int
    limit: int
    items: list

    class Config:
        from_attributes = True

