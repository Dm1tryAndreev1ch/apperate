"""Audit log CRUD operations."""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.crud.base import CRUDBase
from app.models.audit import AuditLog


class CRUDAudit(CRUDBase[AuditLog, dict, dict]):
    """CRUD operations for AuditLog (read-only)."""

    async def get_by_entity(
        self,
        db: AsyncSession,
        *,
        entity: str,
        entity_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """Get audit logs by entity."""
        query = select(AuditLog).where(AuditLog.entity == entity)
        if entity_id:
            query = query.where(AuditLog.entity_id == entity_id)
        query = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()


audit = CRUDAudit(AuditLog)

