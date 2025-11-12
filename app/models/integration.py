"""Integration models."""
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from enum import Enum
from app.database import Base


class BitrixMode(str, Enum):
    """Bitrix integration mode."""

    STUB = "stub"
    LIVE = "live"


class BitrixCallLog(Base):
    """Bitrix API call log (for stub mode and debugging)."""

    __tablename__ = "bitrix_call_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    payload = Column(JSONB, nullable=True)  # Request payload
    response = Column(JSONB, nullable=True)  # Response data
    mode = Column(SQLEnum(BitrixMode), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

