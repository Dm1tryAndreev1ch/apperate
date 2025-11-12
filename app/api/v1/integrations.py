"""Integrations API endpoints."""
from fastapi import APIRouter, Depends
from app.dependencies import get_current_active_user
from app.models.user import User
from app.config import settings
from app.models.integration import BitrixMode

router = APIRouter()


@router.get("/bitrix/status")
async def get_bitrix_status(
    current_user: User = Depends(get_current_active_user),
):
    """Get Bitrix integration status."""
    return {
        "mode": settings.BITRIX_MODE,
        "is_stub": settings.BITRIX_MODE.lower() == BitrixMode.STUB.value,
        "configured": bool(settings.BITRIX_BASE_URL and settings.BITRIX_ACCESS_TOKEN),
    }

