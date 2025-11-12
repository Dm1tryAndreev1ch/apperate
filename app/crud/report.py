"""Report CRUD operations."""
from app.crud.base import CRUDBase
from app.models.report import Report
from app.schemas.report import ReportCreate


class CRUDReport(CRUDBase[Report, ReportCreate, dict]):
    """CRUD operations for Report."""

    pass


report = CRUDReport(Report)

