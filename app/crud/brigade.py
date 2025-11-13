"""CRUD operations for brigades."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.brigade import Brigade, BrigadeDailyScore, brigade_member_association
from app.models.user import User
from app.schemas.brigade import BrigadeCreate, BrigadeUpdate


class CRUDBrigade(CRUDBase[Brigade, BrigadeCreate, BrigadeUpdate]):
    """CRUD helpers for brigades."""

    async def get_with_members(self, db: AsyncSession, *, brigade_id: UUID) -> Optional[Brigade]:
        result = await db.execute(
            select(Brigade)
            .where(Brigade.id == brigade_id)
            .options(selectinload(Brigade.members))
        )
        return result.scalar_one_or_none()

    async def set_members(self, db: AsyncSession, *, brigade: Brigade, member_ids: Optional[List[UUID]]) -> Brigade:
        """Assign members to brigade."""
        if member_ids is None:
            return brigade

        if not member_ids:
            brigade.members = []
        else:
            result = await db.execute(
                select(User).where(User.id.in_(member_ids))
            )
            brigade.members = result.scalars().all()

        db.add(brigade)
        await db.commit()
        await db.refresh(brigade)
        await db.refresh(brigade, attribute_names=["members"])
        return brigade

    async def create(self, db: AsyncSession, *, obj_in: BrigadeCreate) -> Brigade:
        data = obj_in.dict(exclude={"member_ids"})
        brigade = Brigade(**data)
        db.add(brigade)
        await db.commit()
        await db.refresh(brigade)

        await self.set_members(db, brigade=brigade, member_ids=obj_in.member_ids)
        return brigade

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: Brigade,
        obj_in: BrigadeUpdate,
    ) -> Brigade:
        update_data = obj_in.dict(exclude_unset=True, exclude={"member_ids"})
        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)

        if obj_in.member_ids is not None:
            await self.set_members(db, brigade=db_obj, member_ids=obj_in.member_ids)

        return await self.get_with_members(db, brigade_id=db_obj.id) or db_obj


class CRUDBrigadeScore(CRUDBase[BrigadeDailyScore, dict, dict]):
    """CRUD for brigade scores."""

    async def upsert_score(
        self,
        db: AsyncSession,
        *,
        brigade_id: UUID,
        score_date,
        score: float,
        check_id: Optional[UUID] = None,
        details: Optional[dict] = None,
    ) -> BrigadeDailyScore:
        result = await db.execute(
            select(BrigadeDailyScore).where(
                BrigadeDailyScore.brigade_id == brigade_id,
                BrigadeDailyScore.score_date == score_date,
            )
        )
        score_obj = result.scalar_one_or_none()
        if score_obj:
            existing = score_obj.details or {}
            checks = existing.get("checks", [])
            if check_id:
                checks = [entry for entry in checks if entry.get("check_id") != str(check_id)]
                checks.append({"check_id": str(check_id), "score": float(score)})
            total = sum(entry.get("score", 0) for entry in checks) or float(score)
            count = len(checks) or 1
            score_obj.score = total / count
            score_obj.details = {
                "checks": checks,
                "total": total,
                "count": count,
            }
        else:
            score_obj = BrigadeDailyScore(
                brigade_id=brigade_id,
                score_date=score_date,
                score=score,
                details=details
                or {
                    "checks": [{"check_id": str(check_id), "score": float(score)}] if check_id else [],
                    "total": float(score),
                    "count": 1,
                },
            )
        db.add(score_obj)
        await db.commit()
        await db.refresh(score_obj)
        return score_obj


brigade = CRUDBrigade(Brigade)
brigade_score = CRUDBrigadeScore(BrigadeDailyScore)


