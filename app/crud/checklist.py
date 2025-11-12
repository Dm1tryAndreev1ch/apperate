"""Checklist CRUD operations."""
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.base import CRUDBase
from app.models.checklist import ChecklistTemplate, ChecklistTemplateVersion, CheckInstance
from app.schemas.checklist import ChecklistTemplateCreate, ChecklistTemplateUpdate, CheckInstanceCreate, CheckInstanceUpdate


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


class CRUDCheckInstance(CRUDBase[CheckInstance, CheckInstanceCreate, CheckInstanceUpdate]):
    """CRUD operations for CheckInstance."""

    pass


template = CRUDTemplate(ChecklistTemplate)
check_instance = CRUDCheckInstance(CheckInstance)

