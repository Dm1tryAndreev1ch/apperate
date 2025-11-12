"""File schemas."""
from pydantic import BaseModel


class PresignRequest(BaseModel):
    """Presign URL request schema."""

    filename: str
    content_type: str
    size: int


class PresignResponse(BaseModel):
    """Presign URL response schema."""

    upload_url: str
    key: str
    expires_in: int = 3600

