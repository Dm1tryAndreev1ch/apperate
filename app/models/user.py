"""User and Role models."""
from typing import TYPE_CHECKING

from sqlalchemy import Column, String, Boolean, DateTime, Table, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base
from app.models.brigade import brigade_member_association
from app.db.types import EncryptedString, JSONBType, GUID

if TYPE_CHECKING:
    from app.models.brigade import Brigade
    from app.models.report import Report

# Association table for User-Role many-to-many relationship
user_role_association = Table(
    "user_role_association",
    Base.metadata,
    Column("user_id", GUID(), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", GUID(), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    """User model."""

    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(EncryptedString(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    telegram_id = Column(String(100), nullable=True, unique=True, index=True)  # Telegram user ID
    telegram_username = Column(String(100), nullable=True)  # Telegram username
    phone_number = Column(EncryptedString(50), nullable=True)  # Phone number
    contact_info = Column(JSONBType(), nullable=True, default=dict)  # Additional contact information
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    roles = relationship("Role", secondary=user_role_association, back_populates="users")
    brigades = relationship(
        "Brigade",
        secondary=brigade_member_association,
        back_populates="members",
        lazy="selectin",
    )
    leading_brigades = relationship(
        "Brigade",
        foreign_keys="Brigade.leader_id",
        back_populates="leader",
        lazy="selectin",
    )
    authored_reports = relationship(
        "Report",
        foreign_keys="Report.author_id",
        back_populates="author",
        lazy="selectin",
    )
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    notification_preferences = relationship("NotificationPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Role(Base):
    """Role model with permissions."""

    __tablename__ = "roles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    permissions = Column(JSONBType(), nullable=False, default=list)  # List of permission strings
    description = Column(Text, nullable=True)

    # Relationships
    users = relationship("User", secondary=user_role_association, back_populates="roles")

