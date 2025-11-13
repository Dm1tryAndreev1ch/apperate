"""Brigade management endpoints."""
from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.security import Permission
from app.crud.brigade import brigade, brigade_score
from app.database import get_db
from app.dependencies import require_permission
from app.models.user import User
from app.schemas.brigade import (
    BrigadeCreate,
    BrigadeDailyScoreResponse,
    BrigadeResponse,
    BrigadeUpdate,
)

router = APIRouter()


@router.get("", response_model=List[BrigadeResponse])
async def list_brigades(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.BRIGADE_VIEW)),
):
    """List brigades with members."""
    items = await brigade.get_multi(db, skip=skip, limit=limit)
    # preload members
    for item in items:
        await db.refresh(item, attribute_names=["members"])
    return items


@router.post("", response_model=BrigadeResponse, status_code=status.HTTP_201_CREATED)
async def create_brigade(
    payload: BrigadeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.BRIGADE_CREATE)),
):
    """Create new brigade."""
    return await brigade.create(db, obj_in=payload)


@router.get("/{brigade_id}", response_model=BrigadeResponse)
async def get_brigade(
    brigade_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.BRIGADE_VIEW)),
):
    """Fetch brigade by id."""
    brigade_obj = await brigade.get_with_members(db, brigade_id=brigade_id)
    if not brigade_obj:
        raise NotFoundError("Brigade not found")
    return brigade_obj


@router.put("/{brigade_id}", response_model=BrigadeResponse)
async def update_brigade(
    brigade_id: UUID,
    payload: BrigadeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.BRIGADE_UPDATE)),
):
    """Update brigade data."""
    brigade_obj = await brigade.get_with_members(db, brigade_id=brigade_id)
    if not brigade_obj:
        raise NotFoundError("Brigade not found")
    return await brigade.update(db, db_obj=brigade_obj, obj_in=payload)


@router.delete("/{brigade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_brigade(
    brigade_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.BRIGADE_DELETE)),
):
    """Delete brigade."""
    brigade_obj = await brigade.get(db, id=brigade_id)
    if not brigade_obj:
        raise NotFoundError("Brigade not found")
    await brigade.remove(db, id=brigade_id)


@router.get("/{brigade_id}/scores", response_model=List[BrigadeDailyScoreResponse])
async def list_scores(
    brigade_id: UUID,
    skip: int = 0,
    limit: int = 31,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.BRIGADE_SCORE_VIEW)),
):
    """List daily scores for a brigade."""
    return await brigade_score.get_multi(
        db,
        skip=skip,
        limit=limit,
        filters={"brigade_id": brigade_id},
    )


