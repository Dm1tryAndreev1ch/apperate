"""Schemas for demo/test build utilities."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr


class DemoSeedResponse(BaseModel):
    """Response payload for demo data generation."""

    status: Literal["created", "skipped"]
    detail: str
    created_users: int
    created_brigades: int
    created_templates: int
    created_checks: int
    created_reports: int
    created_scores: int
    already_populated: bool


class DemoResetResponse(BaseModel):
    """Response payload for project data reset to the default admin state."""

    status: Literal["reset"]
    detail: str
    records_removed: int
    roles_seeded: int
    admin_email: EmailStr
    admin_password: str


