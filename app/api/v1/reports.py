"""Reports API endpoints."""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import User
from app.models.report import Report, ReportStatus
from app.core.security import Permission
from app.crud.report import report
from app.services.storage_service import storage_service
from app.schemas.report import ReportResponse, ReportDownloadResponse
from app.core.exceptions import NotFoundError

router = APIRouter()


@router.get("", response_model=List[ReportResponse])
async def list_reports(
    skip: int = 0,
    limit: int = 100,
    check_instance_id: Optional[UUID] = None,
    status_filter: Optional[ReportStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List reports with filters."""
    filters = {}
    if check_instance_id:
        filters["check_instance_id"] = check_instance_id
    if status_filter:
        filters["status"] = status_filter

    reports = await report.get_multi(db, skip=skip, limit=limit, filters=filters)
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a report by ID."""
    report_obj = await report.get(db, id=report_id)
    if not report_obj:
        raise NotFoundError("Report not found")
    return report_obj


@router.get("/{report_id}/download", response_model=ReportDownloadResponse)
async def download_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.REPORT_DOWNLOAD)),
):
    """Get presigned URL for downloading a report."""
    report_obj = await report.get(db, id=report_id)
    if not report_obj:
        raise NotFoundError("Report not found")

    if report_obj.status != ReportStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report is not ready. Status: {report_obj.status}",
        )

    if not report_obj.file_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found")

    download_url = storage_service.generate_download_url(report_obj.file_key, expires_in=3600)
    return ReportDownloadResponse(download_url=download_url, expires_in=3600)

