"""Audit log schemas."""
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime


class AuditLogResponse(BaseModel):
    """Audit log response schema."""

    id: UUID
    user_id: Optional[UUID] = None
    entity: str
    entity_id: Optional[UUID] = None
    action: str
    diff: Optional[dict[str, Any]] = None
    timestamp: datetime

    class Config:
        from_attributes = True

