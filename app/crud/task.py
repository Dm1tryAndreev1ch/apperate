"""Task CRUD operations."""
from app.crud.base import CRUDBase
from app.models.task import TaskLocal
from app.schemas.task import TaskLocalCreate


class CRUDTask(CRUDBase[TaskLocal, TaskLocalCreate, dict]):
    """CRUD operations for TaskLocal."""

    pass


task = CRUDTask(TaskLocal)

