"""Schemas for brigade management."""
from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BrigadeBase(BaseModel):
    """Base schema for brigades."""

    name: str
    description: Optional[str] = None
    leader_id: Optional[UUID] = None
    is_active: bool = True
    profile: Optional[Dict[str, str]] = None


class BrigadeCreate(BrigadeBase):
    """Create brigade payload."""

    member_ids: Optional[List[UUID]] = None


class BrigadeUpdate(BaseModel):
    """Update brigade payload."""

    name: Optional[str] = None
    description: Optional[str] = None
    leader_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    profile: Optional[Dict[str, str]] = None
    member_ids: Optional[List[UUID]] = None


class BrigadeMemberResponse(BaseModel):
    """Partial user response for brigade membership."""

    id: UUID
    full_name: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True


class BrigadeSummary(BaseModel):
    """Short brigade reference."""

    id: UUID
    name: str

    class Config:
        from_attributes = True


class BrigadeResponse(BrigadeBase):
    """Response schema for brigades."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    members: List[BrigadeMemberResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class BrigadeDailyScoreBase(BaseModel):
    """Base schema for brigade daily scores."""

    brigade_id: UUID
    score_date: date
    score: float
    details: Optional[Dict[str, float]] = None


class BrigadeDailyScoreCreate(BrigadeDailyScoreBase):
    """Create payload."""

    pass


class BrigadeDailyScoreResponse(BrigadeDailyScoreBase):
    """Response payload."""

    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


