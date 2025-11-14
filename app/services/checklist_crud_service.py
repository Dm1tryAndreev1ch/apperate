"""Checklist CRUD service providing high-level interface for template management."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.crud.checklist import template, check_instance
from app.models.checklist import ChecklistTemplate, ChecklistTemplateVersion, CheckInstance, TemplateStatus
from app.models.user import User
from app.schemas.checklist import ChecklistTemplateCreate, ChecklistTemplateUpdate
from app.services.checklist_service import checklist_service


class ChecklistCRUDService:
    """High-level service for checklist template CRUD operations."""

    @staticmethod
    async def list_templates(
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TemplateStatus] = None,
        search: Optional[str] = None,
    ) -> List[ChecklistTemplate]:
        """List checklist templates with optional filtering."""
        filters: Dict[str, Any] = {}
        if status:
            filters["status"] = status

        templates = await template.get_multi(db, skip=skip, limit=limit, filters=filters)

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            templates = [
                t
                for t in templates
                if search_lower in t.name.lower() or (t.description and search_lower in t.description.lower())
            ]

        return templates

    @staticmethod
    async def get_template(
        db: AsyncSession,
        *,
        template_id: UUID,
    ) -> Optional[ChecklistTemplate]:
        """Get a single template by ID."""
        return await template.get(db, id=template_id)

    @staticmethod
    async def get_template_by_slug(
        db: AsyncSession,
        *,
        slug: str,
    ) -> Optional[ChecklistTemplate]:
        """Get a template by its slug."""
        result = await db.execute(
            select(ChecklistTemplate).where(ChecklistTemplate.name_slug == slug)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_template(
        db: AsyncSession,
        *,
        template_data: ChecklistTemplateCreate,
        created_by: User,
    ) -> ChecklistTemplate:
        """Create a new checklist template."""
        # Validate schema structure
        schema = template_data.schema
        if not isinstance(schema, dict) or "sections" not in schema:
            raise ValueError("Template schema must contain 'sections' array")

        # Validate sections and questions
        sections = schema.get("sections", [])
        if not sections:
            raise ValueError("Template must have at least one section")

        for section in sections:
            if not isinstance(section, dict):
                raise ValueError("Each section must be a dictionary")
            questions = section.get("questions", [])
            if not questions:
                raise ValueError(f"Section '{section.get('title', 'unnamed')}' must have at least one question")

            for question in questions:
                if not isinstance(question, dict):
                    raise ValueError("Each question must be a dictionary")
                if "id" not in question:
                    raise ValueError("Each question must have an 'id' field")
                if "text" not in question and "type" not in question:
                    raise ValueError("Each question must have 'text' and 'type' fields")

        # Create template
        template_obj = await template.create(
            db,
            obj_in={
                **template_data.model_dump(),
                "created_by": created_by.id,
            },
        )

        # Create initial version
        version = ChecklistTemplateVersion(
            template_id=template_obj.id,
            version=1,
            schema=template_obj.schema,
            diff=None,
            created_by=created_by.id,
        )
        db.add(version)
        await db.commit()
        await db.refresh(template_obj)

        return template_obj

    @staticmethod
    async def update_template(
        db: AsyncSession,
        *,
        template_obj: ChecklistTemplate,
        update_data: ChecklistTemplateUpdate,
        updated_by: User,
    ) -> ChecklistTemplate:
        """Update a checklist template, creating a new version if schema changed."""
        old_schema = template_obj.schema
        new_schema = update_data.schema if update_data.schema is not None else old_schema

        # If schema changed, create new version
        if update_data.schema is not None and update_data.schema != old_schema:
            await checklist_service.create_version(
                db,
                template_obj=template_obj,
                new_schema=new_schema,
                created_by=str(updated_by.id),
            )

        # Update template
        update_dict = update_data.model_dump(exclude_unset=True)
        if "schema" in update_dict:
            # Schema already handled via versioning
            update_dict.pop("schema")

        updated_template = await template.update(db, db_obj=template_obj, obj_in=update_dict)
        return updated_template

    @staticmethod
    async def delete_template(
        db: AsyncSession,
        *,
        template_id: UUID,
        soft_delete: bool = True,
    ) -> bool:
        """Delete a template (soft delete by default)."""
        template_obj = await template.get(db, id=template_id)
        if not template_obj:
            return False

        if soft_delete:
            # Soft delete: mark as archived
            template_obj.status = TemplateStatus.ARCHIVED
            db.add(template_obj)
            await db.commit()
        else:
            # Hard delete: remove from database
            await template.remove(db, id=template_id)

        return True

    @staticmethod
    async def clone_template(
        db: AsyncSession,
        *,
        template_id: UUID,
        new_name: str,
        created_by: User,
    ) -> ChecklistTemplate:
        """Clone an existing template with a new name."""
        source_template = await template.get(db, id=template_id)
        if not source_template:
            raise ValueError(f"Template {template_id} not found")

        # Create new template based on source
        new_template_data = ChecklistTemplateCreate(
            name=new_name,
            description=f"Копия: {source_template.description or source_template.name}",
            schema=source_template.schema,
        )

        return await ChecklistCRUDService.create_template(
            db,
            template_data=new_template_data,
            created_by=created_by,
        )

    @staticmethod
    async def get_template_versions(
        db: AsyncSession,
        *,
        template_id: UUID,
    ) -> List[ChecklistTemplateVersion]:
        """Get all versions of a template."""
        return await template.get_versions(db, template_id=template_id)

    @staticmethod
    async def restore_template_version(
        db: AsyncSession,
        *,
        template_id: UUID,
        version: int,
        restored_by: User,
    ) -> ChecklistTemplate:
        """Restore a template to a specific version."""
        template_obj = await template.get(db, id=template_id)
        if not template_obj:
            raise ValueError(f"Template {template_id} not found")

        # Get version
        versions = await template.get_versions(db, template_id=template_id)
        target_version = next((v for v in versions if v.version == version), None)
        if not target_version:
            raise ValueError(f"Version {version} not found for template {template_id}")

        # Create new version with restored schema
        await checklist_service.create_version(
            db,
            template_obj=template_obj,
            new_schema=target_version.schema,
            created_by=str(restored_by.id),
        )

        await db.refresh(template_obj)
        return template_obj


checklist_crud_service = ChecklistCRUDService()

