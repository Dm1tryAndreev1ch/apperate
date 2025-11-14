"""Endpoints for generating demo data (test build)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Permission
from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.demo import DemoSeedResponse, DemoResetResponse
from app.services.demo_service import (
    generate_demo_data,
    reset_project_to_clean_state,
)

router = APIRouter()


@router.post("/test-build", response_model=DemoSeedResponse)
async def create_test_build(
    current_user: User = Depends(require_permission(Permission.USER_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> DemoSeedResponse:
    """Generate fake data for demo environments."""
    try:
        payload = await generate_demo_data(db, current_user)
        return DemoSeedResponse(**payload)
    except Exception as e:
        import traceback
        error_detail = str(e)
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при создании демо-данных: {error_detail}"
        )


@router.post("/reset", response_model=DemoResetResponse)
async def reset_project(
    current_user: User = Depends(require_permission(Permission.USER_DELETE)),
    db: AsyncSession = Depends(get_db),
) -> DemoResetResponse:
    """Reset project data to a clean state with only the default admin."""
    payload = await reset_project_to_clean_state(db)
    return DemoResetResponse(**payload)


