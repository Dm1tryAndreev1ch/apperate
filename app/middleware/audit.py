"""Audit logging middleware."""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime
from typing import Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from uuid import UUID
import json
from app.config import settings
from app.models.audit import AuditLog
from app.utils.security import decode_token

# Create async engine for audit logging
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for logging API actions to audit log."""

    # Methods that modify data
    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    # Paths to exclude from audit logging
    EXCLUDED_PATHS = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log audit information."""
        # Skip audit for excluded paths
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        # Skip audit for read-only methods (unless explicitly needed)
        if request.method not in self.WRITE_METHODS:
            return await call_next(request)

        # Extract user from token
        user_id = None
        try:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                user_id = payload.get("sub")
        except Exception:
            pass  # User not authenticated or invalid token

        # Process request
        response = await call_next(request)

        # Log to audit if status indicates success
        if 200 <= response.status_code < 300:
            try:
                await self._log_action(
                    user_id=user_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                )
            except Exception:
                pass  # Don't fail request if audit logging fails

        return response

    async def _log_action(
        self,
        user_id: Optional[str],
        method: str,
        path: str,
        status_code: int,
    ):
        """Log action to audit log."""
        # Determine entity type from path
        entity = "unknown"
        entity_id = None

        # Extract entity from path (e.g., /api/users/{id} -> entity=user, entity_id={id})
        path_parts = path.strip("/").split("/")
        if len(path_parts) >= 3:
            entity = path_parts[1]  # e.g., "users", "checks", "templates"
            if len(path_parts) >= 3 and path_parts[2]:
                try:
                    entity_id = UUID(path_parts[2])
                except ValueError:
                    pass

        # Determine action from method
        action_map = {
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete",
        }
        action = action_map.get(method, method.lower())

        async with AsyncSessionLocal() as db:
            audit_entry = AuditLog(
                user_id=UUID(user_id) if user_id else None,
                entity=entity,
                entity_id=entity_id,
                action=action,
                diff=None,  # Could be enhanced to capture request/response diff
                timestamp=datetime.utcnow(),
            )
            db.add(audit_entry)
            await db.commit()


def setup_audit_middleware(app) -> None:
    """Setup audit logging middleware."""
    app.add_middleware(AuditMiddleware)
