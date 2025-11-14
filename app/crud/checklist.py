"""Checklist CRUD operations."""
from typing import Any, Dict, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.checklist import ChecklistTemplate, ChecklistTemplateVersion, CheckInstance
from app.schemas.checklist import ChecklistTemplateCreate, ChecklistTemplateUpdate, CheckInstanceCreate, CheckInstanceUpdate
from app.utils.slugify import slugify


class CRUDTemplate(CRUDBase[ChecklistTemplate, ChecklistTemplateCreate, ChecklistTemplateUpdate]):
    """CRUD operations for ChecklistTemplate."""

    async def get_versions(self, db: AsyncSession, *, template_id: UUID):
        """Get all versions of a template."""
        result = await db.execute(
            select(ChecklistTemplateVersion)
            .where(ChecklistTemplateVersion.template_id == template_id)
            .order_by(ChecklistTemplateVersion.version.desc())
        )
        return result.scalars().all()

    async def _generate_unique_slug(
        self,
        db: AsyncSession,
        base_slug: str,
        *,
        exclude_id: Optional[UUID] = None,
    ) -> str:
        """Ensure slug uniqueness by appending numeric suffix if needed."""
        candidate = base_slug or "template"
        suffix = 1

        while True:
            query = select(ChecklistTemplate.id).where(ChecklistTemplate.name_slug == candidate)
            if exclude_id:
                query = query.where(ChecklistTemplate.id != exclude_id)
            result = await db.execute(query.limit(1))
            if result.scalar_one_or_none() is None:
                return candidate
            suffix += 1
            candidate = f"{base_slug}-{suffix}"

    async def create(self, db: AsyncSession, *, obj_in: ChecklistTemplateCreate) -> ChecklistTemplate:
        """Create a new checklist template ensuring slug uniqueness."""
        if isinstance(obj_in, dict):
            obj_in_data: Dict[str, Any] = obj_in
        else:
            obj_in_data = obj_in.model_dump(exclude_unset=True, mode="python")

        slug_source = obj_in_data.get("name_slug") or obj_in_data.get("name")
        obj_in_data["name_slug"] = await self._generate_unique_slug(db, slugify(slug_source))

        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ChecklistTemplate,
        obj_in: ChecklistTemplateUpdate | Dict[str, Any],
    ) -> ChecklistTemplate:
        """Update a template, recalculating slug if needed."""
        if isinstance(obj_in, dict):
            update_data: Dict[str, Any] = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True, mode="python")

        if "name_slug" in update_data or "name" in update_data:
            slug_source = update_data.get("name_slug") or update_data.get("name") or db_obj.name
            update_data["name_slug"] = await self._generate_unique_slug(
                db,
                slugify(slug_source),
                exclude_id=db_obj.id,
            )

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj


class CRUDCheckInstance(CRUDBase[CheckInstance, CheckInstanceCreate, CheckInstanceUpdate]):
    """CRUD operations for CheckInstance."""

    pass


template = CRUDTemplate(ChecklistTemplate)
check_instance = CRUDCheckInstance(CheckInstance)

