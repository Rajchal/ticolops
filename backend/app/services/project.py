"""Project service for handling project-related business logic."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.orm import selectinload, joinedload

from app.models.project import Project, ProjectFile, Deployment, ProjectStatus, ProjectRole, project_members
from app.models.user import User
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, Project as ProjectSchema,
    ProjectFileCreate, ProjectFileUpdate, ProjectFile as ProjectFileSchema,
    DeploymentCreate, DeploymentUpdate, Deployment as DeploymentSchema,
    ProjectMember, ProjectStats, BulkFileOperation
)
from app.core.exceptions import NotFoundError, PermissionError, ValidationError
import logging

logger = logging.getLogger(__name__)


class ProjectService:
    """Service class for project-related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(self, project_data: ProjectCreate, owner_id: str) -> ProjectSchema:
        """Create a new project."""
        # Create project with default settings
        db_project = Project(
            name=project_data.name,
            description=project_data.description,
            status=project_data.status.value,
            owner_id=UUID(owner_id),
            settings=project_data.settings.dict() if project_data.settings else {},
            metadata_info=project_data.metadata_info or {}
        )
        
        try:
            self.db.add(db_project)
            await self.db.commit()
            # Refresh can trigger relationship loader codepaths that may not be
            # fully initialized in demo environments (nullable loader impls).
            # Attempt a best-effort refresh but don't fail the whole request if
            # SQLAlchemy raises during refresh — we'll re-query via get_project
            # below which fetches the canonical state.
            try:
                await self.db.refresh(db_project)
            except Exception:
                logger.exception("Non-fatal error while refreshing db_project; continuing to fetch via get_project")

            # Add owner as a member with OWNER role
            await self._add_project_member(str(db_project.id), owner_id, ProjectRole.OWNER)

            return await self.get_project(str(db_project.id), owner_id)
        except Exception as e:
            # Log helpful context for debugging intermittent failures during post-create processing
            try:
                logger.exception("Failed while creating project; project_data=%s owner_id=%s db_project=%s", project_data, owner_id, getattr(db_project, 'id', None))
            except Exception:
                logger.exception("Failed while creating project; (unable to format debug context)")
            # Attempt to rollback to keep session usable
            try:
                await self.db.rollback()
            except Exception:
                logger.exception("Rollback failed after create_project exception")
            raise

    async def get_project(self, project_id: str, user_id: str) -> ProjectSchema:
        """Get a project by ID with member validation."""
        # Check if user has access to the project
        if not await self._user_has_project_access(project_id, user_id):
            raise PermissionError("You don't have access to this project")
        
        # Get project with related data. In lightweight/demo DBs some related
        # tables (like project_files) may be missing; that would raise a
        # ProgrammingError from the DB. Detect that and fall back to a simpler
        # query that only selects the Project row so the API can still return
        # a usable response.
        query = (
            select(Project)
            .options(
                selectinload(Project.owner),
                selectinload(Project.members),
                selectinload(Project.files),
                selectinload(Project.deployments)
            )
            .where(Project.id == UUID(project_id))
        )

        missing_related_tables = False
        try:
            result = await self.db.execute(query)
            db_project = result.scalar_one_or_none()
        except Exception as exc:
            # If a related table is missing (UndefinedTable / ProgrammingError),
            # log and retry with a simple select to avoid failing the whole request.
            msg = str(exc).lower()
            if "does not exist" in msg or "undefinedtableerror" in msg or "relation \"project_files\"" in msg:
                logger.warning("Related table missing while loading project: %s; falling back to simple project query", exc)
                # The failed attempt put the transaction into an aborted state; rollback
                # to clear it before issuing new queries.
                try:
                    await self.db.rollback()
                except Exception:
                    logger.exception("Failed to rollback after related-table error")
                simple_q = select(Project).where(Project.id == UUID(project_id))
                result = await self.db.execute(simple_q)
                db_project = result.scalar_one_or_none()
                missing_related_tables = True
            else:
                raise

        if not db_project:
            raise NotFoundError("Project not found")
        
        # Convert to schema with additional data
        def _dt_iso(v):
            return v.isoformat() if v is not None else None

        project_dict = {
            "id": str(db_project.id),
            "name": db_project.name,
            "description": db_project.description,
            "status": str(db_project.status) if db_project.status is not None else "active",
            "owner_id": str(db_project.owner_id),
            "settings": db_project.settings or {},
            "metadata_info": db_project.metadata_info or {},
            "created_at": _dt_iso(db_project.created_at),
            "updated_at": _dt_iso(db_project.updated_at),
            "last_activity": _dt_iso(db_project.last_activity),
            # If related tables were missing, avoid touching relationship
            # attributes which would trigger additional DB queries that fail.
            "file_count": (len(db_project.files) if not missing_related_tables and getattr(db_project, 'files', None) is not None else 0),
            "deployment_count": (len(db_project.deployments) if not missing_related_tables and getattr(db_project, 'deployments', None) is not None else 0)
        }
        
        # Get project members with roles
        members = await self._get_project_members(project_id)
        project_dict["members"] = members
        
        return ProjectSchema(**project_dict)

    async def update_project(self, project_id: str, project_data: ProjectUpdate, user_id: str) -> ProjectSchema:
        """Update a project."""
        # Check if user is owner or has edit permissions
        if not await self._user_can_edit_project(project_id, user_id):
            raise PermissionError("You don't have permission to edit this project")
        
        # Build update data
        update_data = {}
        if project_data.name is not None:
            update_data["name"] = project_data.name
        if project_data.description is not None:
            update_data["description"] = project_data.description
        if project_data.status is not None:
            update_data["status"] = project_data.status.value
        if project_data.settings is not None:
            update_data["settings"] = project_data.settings.dict()
        if project_data.metadata_info is not None:
            update_data["metadata_info"] = project_data.metadata_info
        
        if update_data:
            update_data["updated_at"] = datetime.utcnow()
            
            query = (
                update(Project)
                .where(Project.id == UUID(project_id))
                .values(**update_data)
            )
            
            await self.db.execute(query)
            await self.db.commit()
        
        return await self.get_project(project_id, user_id)

    async def delete_project(self, project_id: str, user_id: str) -> bool:
        """Delete a project (only owner can delete)."""
        # Check if user is the owner
        query = select(Project).where(
            and_(Project.id == UUID(project_id), Project.owner_id == UUID(user_id))
        )
        result = await self.db.execute(query)
        db_project = result.scalar_one_or_none()
        
        if not db_project:
            raise PermissionError("Only the project owner can delete the project")
        
        # Delete project (cascade will handle related records)
        await self.db.delete(db_project)
        await self.db.commit()
        
        return True

    async def get_user_projects(self, user_id: str, status: Optional[ProjectStatus] = None) -> List[ProjectSchema]:
        """Get all projects for a user."""
        # Query for projects where user is owner or member
        # Select only scalar columns to avoid DISTINCT over JSON/jsonb columns
        cols = [
            Project.id, Project.name, Project.description, Project.owner_id,
            Project.created_at, Project.updated_at, Project.last_activity
        ]

        query = (
            select(*cols)
            .join(project_members, Project.id == project_members.c.project_id, isouter=True)
            .where(
                or_(
                    Project.owner_id == UUID(user_id),
                    project_members.c.user_id == UUID(user_id)
                )
            )
        )

        if status:
            query = query.where(Project.status == status.value)

        query = query.order_by(Project.updated_at.desc())

        result = await self.db.execute(query)
        rows = result.all()

        projects = []
        def _iso(v):
            return v.isoformat() if v is not None else None

        for id_, name, description, owner_id, created_at, updated_at, last_activity in rows:
            projects.append(ProjectSchema(
                id=str(id_),
                name=name,
                description=description,
                status="active",
                owner_id=str(owner_id) if owner_id else None,
                settings={},
                metadata_info={},
                created_at=_iso(created_at),
                updated_at=_iso(updated_at)
            ))

        return projects

    async def add_project_member(self, project_id: str, user_email: str, role: ProjectRole, inviter_id: str) -> ProjectMember:
        """Add a member to a project."""
        # Check if inviter has permission
        if not await self._user_can_edit_project(project_id, inviter_id):
            raise PermissionError("You don't have permission to add members to this project")
        
        # Find user by email
        query = select(User).where(User.email == user_email)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("User not found")
        
        # Check if user is already a member
        if await self._user_has_project_access(project_id, str(user.id)):
            raise ValidationError("User is already a member of this project")
        
        # Add member
        return await self._add_project_member(project_id, str(user.id), role, inviter_id)

    async def remove_project_member(self, project_id: str, user_id: str, remover_id: str) -> bool:
        """Remove a member from a project."""
        # Check permissions
        if not await self._user_can_edit_project(project_id, remover_id):
            raise PermissionError("You don't have permission to remove members")
        
        # Can't remove the owner
        query = select(Project).where(Project.id == UUID(project_id))
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if project and str(project.owner_id) == user_id:
            raise ValidationError("Cannot remove the project owner")
        
        # Remove member
        query = delete(project_members).where(
            and_(
                project_members.c.project_id == UUID(project_id),
                project_members.c.user_id == UUID(user_id)
            )
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        return result.rowcount > 0

    async def update_member_role(self, project_id: str, user_id: str, new_role: ProjectRole, updater_id: str) -> ProjectMember:
        """Update a member's role in a project."""
        # Check permissions
        if not await self._user_can_edit_project(project_id, updater_id):
            raise PermissionError("You don't have permission to update member roles")
        
        # Can't change owner role
        query = select(Project).where(Project.id == UUID(project_id))
        result = await self.db.execute(query)
        project = result.scalar_one_or_none()
        
        if project and str(project.owner_id) == user_id:
            raise ValidationError("Cannot change the project owner's role")
        
        # Update role
        query = (
            update(project_members)
            .where(
                and_(
                    project_members.c.project_id == UUID(project_id),
                    project_members.c.user_id == UUID(user_id)
                )
            )
            .values(role=new_role.value)
        )
        
        result = await self.db.execute(query)
        await self.db.commit()
        
        if result.rowcount == 0:
            raise NotFoundError("Member not found in project")
        
        # Return updated member info
        members = await self._get_project_members(project_id)
        for member in members:
            if member.user_id == user_id:
                return member
        
        raise NotFoundError("Updated member not found")

    async def get_project_stats(self, project_id: str, user_id: str) -> ProjectStats:
        """Get project statistics."""
        if not await self._user_has_project_access(project_id, user_id):
            raise PermissionError("You don't have access to this project")
        
        # Get file statistics
        file_query = (
            select(
                func.count(ProjectFile.id).label("total_files"),
                func.coalesce(func.sum(func.cast(ProjectFile.size, func.INTEGER)), 0).label("total_size"),
                func.max(ProjectFile.updated_at).label("last_modified")
            )
            .where(
                and_(
                    ProjectFile.project_id == UUID(project_id),
                    ProjectFile.is_deleted == False
                )
            )
        )
        
        file_result = await self.db.execute(file_query)
        file_stats = file_result.first()
        
        # Get member count
        member_query = (
            select(func.count(project_members.c.user_id))
            .where(project_members.c.project_id == UUID(project_id))
        )
        
        member_result = await self.db.execute(member_query)
        member_count = member_result.scalar()
        
        # Get deployment count
        deployment_query = (
            select(func.count(Deployment.id))
            .where(Deployment.project_id == UUID(project_id))
        )
        
        deployment_result = await self.db.execute(deployment_query)
        deployment_count = deployment_result.scalar()
        
        return ProjectStats(
            total_files=file_stats.total_files or 0,
            total_size=str(file_stats.total_size or 0),
            last_modified=file_stats.last_modified or datetime.utcnow(),
            active_collaborators=member_count or 0,
            total_deployments=deployment_count or 0,
            recent_activity=[]  # TODO: Implement activity tracking
        )

    # Private helper methods
    async def _user_has_project_access(self, project_id: str, user_id: str) -> bool:
        """Check if user has access to a project."""
        query = (
            select(Project)
            .join(project_members, Project.id == project_members.c.project_id, isouter=True)
            .where(
                and_(
                    Project.id == UUID(project_id),
                    or_(
                        Project.owner_id == UUID(user_id),
                        project_members.c.user_id == UUID(user_id)
                    )
                )
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def _user_can_edit_project(self, project_id: str, user_id: str) -> bool:
        """Check if user can edit a project (owner or collaborator)."""
        query = (
            select(Project)
            .join(project_members, Project.id == project_members.c.project_id, isouter=True)
            .where(
                and_(
                    Project.id == UUID(project_id),
                    or_(
                        Project.owner_id == UUID(user_id),
                        and_(
                            project_members.c.user_id == UUID(user_id),
                            project_members.c.role.in_([ProjectRole.OWNER.value, ProjectRole.COLLABORATOR.value])
                        )
                    )
                )
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def _add_project_member(self, project_id: str, user_id: str, role: ProjectRole, inviter_id: Optional[str] = None) -> ProjectMember:
        """Add a member to a project."""
        # Insert into association table
        insert_data = {
            "project_id": UUID(project_id),
            "user_id": UUID(user_id),
            "role": role.value,
            "joined_at": datetime.utcnow()
        }
        
        if inviter_id:
            insert_data["invited_by"] = UUID(inviter_id)
        
        try:
            query = project_members.insert().values(**insert_data)
            await self.db.execute(query)
            await self.db.commit()

            # Get user info for response
            user_query = select(User).where(User.id == UUID(user_id))
            user_result = await self.db.execute(user_query)
            user = user_result.scalar_one_or_none()

            if user is None:
                logger.error("_add_project_member: inserted membership but user row not found user_id=%s project_id=%s", user_id, project_id)
                raise NotFoundError("User not found after adding member")

            return ProjectMember(
                user_id=str(user.id),
                name=getattr(user, 'name', '') or '',
                email=getattr(user, 'email', '') or '',
                role=role,
                joined_at=insert_data["joined_at"].isoformat() if isinstance(insert_data.get("joined_at"), datetime) else insert_data.get("joined_at"),
                invited_by=str(inviter_id) if inviter_id else None
            )
        except Exception as e:
            logger.exception("Error adding project member: project_id=%s user_id=%s role=%s inviter_id=%s", project_id, user_id, role, inviter_id)
            try:
                await self.db.rollback()
            except Exception:
                logger.exception("Rollback failed in _add_project_member")
            raise

    async def _get_project_members(self, project_id: str) -> List[ProjectMember]:
        """Get all members of a project."""
        # Build column list dynamically because some demo DBs may not have the
        # `invited_by` column in the legacy `project_members` table.
        cols = [User, project_members.c.role, project_members.c.joined_at]
        include_invited_by = hasattr(project_members.c, 'invited_by')
        if include_invited_by:
            cols.append(project_members.c.invited_by)

        query = (
            select(*cols)
            .join(project_members, User.id == project_members.c.user_id)
            .where(project_members.c.project_id == UUID(project_id))
            .order_by(project_members.c.joined_at)
        )

        result = await self.db.execute(query)
        rows = result.all()

        members: List[ProjectMember] = []
        for row in rows:
            # row tuple may be (user, role, joined_at) or (user, role, joined_at, invited_by)
            user = row[0]
            role = row[1]
            joined_at = row[2]
            invited_by = row[3] if include_invited_by and len(row) > 3 else None

            members.append(ProjectMember(
                user_id=str(user.id),
                name=user.name,
                email=user.email,
                role=ProjectRole(role),
                joined_at=joined_at.isoformat() if getattr(joined_at, 'isoformat', None) else joined_at,
                invited_by=str(invited_by) if invited_by else None
            ))

        return members