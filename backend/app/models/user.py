"""
User database models using SQLAlchemy.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Enum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base


class UserRoleEnum(enum.Enum):
    """User role enumeration for database."""
    STUDENT = "student"
    COORDINATOR = "coordinator"
    ADMIN = "admin"


class UserStatusEnum(enum.Enum):
    """User status enumeration for database."""
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


class User(Base):
    """User database model."""
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    avatar = Column(Text, nullable=True)
    role = Column(
        Enum(UserRoleEnum),
        default=UserRoleEnum.STUDENT,
        nullable=False
    )
    status = Column(
        Enum(UserStatusEnum),
        default=UserStatusEnum.OFFLINE,
        nullable=False
    )
    last_activity = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    preferences = Column(
        JSONB,
        default={
            "email_notifications": True,
            "push_notifications": True,
            "activity_visibility": True,
            "conflict_alerts": True,
            "deployment_notifications": True
        },
        nullable=False
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships (will be imported when activity models are loaded)
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    presence_records = relationship("UserPresence", back_populates="user", cascade="all, delete-orphan")
    activity_summaries = relationship("ActivitySummary", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, name={self.name})>"