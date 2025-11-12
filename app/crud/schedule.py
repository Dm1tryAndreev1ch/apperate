"""Schedule CRUD operations."""
from app.crud.base import CRUDBase
from app.models.schedule import Schedule
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate


class CRUDSchedule(CRUDBase[Schedule, ScheduleCreate, ScheduleUpdate]):
    """CRUD operations for Schedule."""

    pass


schedule = CRUDSchedule(Schedule)

