"""Audit logs API endpoints (Admin, read-only)."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import User
from app.core.security import Permission
from app.crud.audit import audit
from app.schemas.audit import AuditLogResponse

router = APIRouter()


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    skip: int = 0,
    limit: int = 100,
    entity: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[UUID] = Query(None, description="Filter by entity ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.AUDIT_VIEW)),
):
    """List audit logs (read-only)."""
    if entity:
        logs = await audit.get_by_entity(
            db,
            entity=entity,
            entity_id=str(entity_id) if entity_id else None,
            skip=skip,
            limit=limit,
        )
    else:
        logs = await audit.get_multi(db, skip=skip, limit=limit)
    return logs

