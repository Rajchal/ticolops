"""
Repository database models using SQLAlchemy.
"""

from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum

from app.core.database import Base


class GitProvider(enum.Enum):
    """Git provider enumeration for database."""
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"


class Repository(Base):
    """Repository database model."""
    __tablename__ = "repositories"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    project_id = Column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name = Column(String(200), nullable=False)
    url = Column(Text, nullable=False)
    provider = Column(
        Enum(GitProvider),
        nullable=False
    )
    branch = Column(String(100), default="main", nullable=False)
    webhook_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    deployment_config = Column(
        JSONB,
        default={
            "auto_deploy": True,
            "build_command": "",
            "output_directory": "",
            "environment_variables": {}
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

    # Relationships
    project = relationship("Project", back_populates="repositories")
    deployments = relationship("Deployment", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Repository(id={self.id}, name={self.name}, project_id={self.project_id})>"