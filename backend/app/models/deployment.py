"""
Deployment database models using SQLAlchemy.
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base


class DeploymentStatus(enum.Enum):
    """Deployment status enumeration for database."""
    PENDING = "pending"
    BUILDING = "building"
    SUCCESS = "success"
    FAILED = "failed"


class Deployment(Base):
    """Deployment database model."""
    __tablename__ = "deployments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    repository_id = Column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    branch = Column(String(100), nullable=False)
    commit_hash = Column(String(40), nullable=False)
    status = Column(
        Enum(DeploymentStatus),
        default=DeploymentStatus.PENDING,
        nullable=False,
        index=True
    )
    url = Column(Text, nullable=True)
    logs = Column(ARRAY(Text), default=[], nullable=False)
    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True
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

    # Relationships
    repository = relationship("Repository", back_populates="deployments")

    def __repr__(self):
        return f"<Deployment(id={self.id}, repository_id={self.repository_id}, status={self.status})>"