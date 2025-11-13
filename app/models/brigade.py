"""Brigade domain models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.db.types import EncryptedString, JSONBType, GUID


# Association table linking users to brigades
brigade_member_association = Table(
    "brigade_members",
    Base.metadata,
    Column(
        "brigade_id",
        GUID(),
        ForeignKey("brigades.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "user_id",
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "joined_at",
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    ),
)


class Brigade(Base):
    """Production brigade (crew) entity."""

    __tablename__ = "brigades"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(EncryptedString(1024), nullable=True)
    leader_id = Column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    profile = Column(JSONBType(), nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    leader = relationship("User", foreign_keys=[leader_id], back_populates="leading_brigades")
    members = relationship(
        "User",
        secondary=brigade_member_association,
        back_populates="brigades",
        lazy="selectin",
    )
    daily_scores = relationship(
        "BrigadeDailyScore",
        back_populates="brigade",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    checks = relationship(
        "CheckInstance",
        back_populates="brigade",
        cascade="all",
        passive_deletes=True,
    )


class BrigadeDailyScore(Base):
    """Aggregated daily score for a brigade."""

    __tablename__ = "brigade_daily_scores"
    __table_args__ = (
        UniqueConstraint("brigade_id", "score_date", name="uq_brigade_score_day"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    brigade_id = Column(
        GUID(),
        ForeignKey("brigades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score_date = Column(Date, nullable=False, index=True)
    score = Column(Numeric(10, 2), nullable=False, default=0)
    details = Column(JSONBType(), nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    brigade = relationship("Brigade", back_populates="daily_scores")


