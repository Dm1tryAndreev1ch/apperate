"""Files API endpoints."""
from fastapi import APIRouter, Depends
from app.dependencies import get_current_active_user
from app.models.user import User
from app.services.storage_service import storage_service
from app.schemas.files import PresignRequest, PresignResponse
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/presign", response_model=PresignResponse)
async def generate_presigned_url(
    request: PresignRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Generate presigned URL for file upload."""
    # Generate unique key for the file
    file_extension = request.filename.split(".")[-1] if "." in request.filename else ""
    key = f"uploads/{current_user.id}/{datetime.utcnow().strftime('%Y/%m/%d')}/{uuid.uuid4()}.{file_extension}"

    # Generate presigned URL
    upload_url = storage_service.generate_upload_url(
        key=key,
        content_type=request.content_type,
        expires_in=3600,
    )

    return PresignResponse(
        upload_url=upload_url,
        key=key,
        expires_in=3600,
    )

