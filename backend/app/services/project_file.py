"""Project file service for handling file-related operations."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func

from app.models.project import ProjectFile, Project
from app.schemas.project import (
    ProjectFileCreate, ProjectFileUpdate, ProjectFile as ProjectFileSchema,
    BulkFileOperation, FileType
)
from app.core.exceptions import NotFoundError, PermissionError, ValidationError
from app.services.project import ProjectService


class ProjectFileService:
    """Service class for project file operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_service = ProjectService(db)

    async def create_file(self, project_id: str, file_data: ProjectFileCreate, user_id: str) -> ProjectFileSchema:
        """Create a new file in a project."""
        # Check if user has access to the project
        if not await self.project_service._user_has_project_access(project_id, user_id):
            raise PermissionError("You don't have access to this project")
        
        # Check if file already exists at the same path
        existing_query = (
            select(ProjectFile)
            .where(
                and_(
                    ProjectFile.project_id == UUID(project_id),
                    ProjectFile.path == file_data.path,
                    ProjectFile.is_deleted == False
                )
            )
        )
        
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise ValidationError("A file already exists at this path")
        
        # Calculate file size
        file_size = str(len(file_data.content.encode('utf-8'))) if file_data.content else "0"
        
        # Create file
        db_file = ProjectFile(
            project_id=UUID(project_id),
            name=file_data.name,
            path=file_data.path,
            content=file_data.content,
            file_type=file_data.file_type.value,
            size=file_size,
            created_by=UUID(user_id),
            last_modified_by=UUID(user_id)
        )
        
        self.db.add(db_file)
        await self.db.commit()
        await self.db.refresh(db_file)
        
        # Update project last activity
        await self._update_project_activity(project_id)
        
        return self._convert_to_schema(db_file)

    async def get_file(self, file_id: str, user_id: str) -> ProjectFileSchema:
        """Get a file by ID."""
        query = (
            select(ProjectFile)
            .where(
                and_(
                    ProjectFile.id == UUID(file_id),
                    ProjectFile.is_deleted == False
                )
            )
        )
        
        result = await self.db.execute(query)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise NotFoundError("File not found")
        
        # Check if user has access to the project
        if not await self.project_service._user_has_project_access(str(db_file.project_id), user_id):
            raise PermissionError("You don't have access to this file")
        
        return self._convert_to_schema(db_file)

    async def update_file(self, file_id: str, file_data: ProjectFileUpdate, user_id: str) -> ProjectFileSchema:
        """Update a file."""
        # Get the file
        query = (
            select(ProjectFile)
            .where(
                and_(
                    ProjectFile.id == UUID(file_id),
                    ProjectFile.is_deleted == False
                )
            )
        )
        
        result = await self.db.execute(query)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise NotFoundError("File not found")
        
        # Check if user has access to the project
        if not await self.project_service._user_can_edit_project(str(db_file.project_id), user_id):
            raise PermissionError("You don't have permission to edit this file")
        
        # Build update data
        update_data = {"last_modified_by": UUID(user_id), "updated_at": datetime.utcnow()}
        
        if file_data.name is not None:
            update_data["name"] = file_data.name
        if file_data.path is not None:
            # Check if new path conflicts with existing files
            if file_data.path != db_file.path:
                existing_query = (
                    select(ProjectFile)
                    .where(
                        and_(
                            ProjectFile.project_id == db_file.project_id,
                            ProjectFile.path == file_data.path,
                            ProjectFile.id != UUID(file_id),
                            ProjectFile.is_deleted == False
                        )
                    )
                )
                
                existing_result = await self.db.execute(existing_query)
                if existing_result.scalar_one_or_none():
                    raise ValidationError("A file already exists at this path")
            
            update_data["path"] = file_data.path
        
        if file_data.content is not None:
            update_data["content"] = file_data.content
            update_data["size"] = str(len(file_data.content.encode('utf-8')))
            # Increment version
            current_version = db_file.version
            try:
                version_parts = current_version.split('.')
                patch_version = int(version_parts[-1]) + 1
                version_parts[-1] = str(patch_version)
                update_data["version"] = '.'.join(version_parts)
            except (ValueError, IndexError):
                update_data["version"] = "1.0.1"
        
        if file_data.file_type is not None:
            update_data["file_type"] = file_data.file_type.value
        
        # Update file
        update_query = (
            update(ProjectFile)
            .where(ProjectFile.id == UUID(file_id))
            .values(**update_data)
        )
        
        await self.db.execute(update_query)
        await self.db.commit()
        
        # Update project last activity
        await self._update_project_activity(str(db_file.project_id))
        
        # Return updated file
        return await self.get_file(file_id, user_id)

    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete a file (soft delete)."""
        # Get the file
        query = (
            select(ProjectFile)
            .where(
                and_(
                    ProjectFile.id == UUID(file_id),
                    ProjectFile.is_deleted == False
                )
            )
        )
        
        result = await self.db.execute(query)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise NotFoundError("File not found")
        
        # Check if user has access to the project
        if not await self.project_service._user_can_edit_project(str(db_file.project_id), user_id):
            raise PermissionError("You don't have permission to delete this file")
        
        # Soft delete
        update_query = (
            update(ProjectFile)
            .where(ProjectFile.id == UUID(file_id))
            .values(
                is_deleted=True,
                updated_at=datetime.utcnow(),
                last_modified_by=UUID(user_id)
            )
        )
        
        await self.db.execute(update_query)
        await self.db.commit()
        
        # Update project last activity
        await self._update_project_activity(str(db_file.project_id))
        
        return True

    async def get_project_files(self, project_id: str, user_id: str, file_type: Optional[FileType] = None) -> List[ProjectFileSchema]:
        """Get all files in a project."""
        # Check if user has access to the project
        if not await self.project_service._user_has_project_access(project_id, user_id):
            raise PermissionError("You don't have access to this project")
        
        query = (
            select(ProjectFile)
            .where(
                and_(
                    ProjectFile.project_id == UUID(project_id),
                    ProjectFile.is_deleted == False
                )
            )
        )
        
        if file_type:
            query = query.where(ProjectFile.file_type == file_type.value)
        
        query = query.order_by(ProjectFile.path, ProjectFile.name)
        
        result = await self.db.execute(query)
        db_files = result.scalars().all()
        
        return [self._convert_to_schema(db_file) for db_file in db_files]

    async def bulk_file_operation(self, project_id: str, operation: BulkFileOperation, user_id: str) -> Dict[str, int]:
        """Perform bulk operations on files."""
        # Check if user has access to the project
        if not await self.project_service._user_can_edit_project(project_id, user_id):
            raise PermissionError("You don't have permission to perform bulk operations")
        
        if operation.operation == "delete":
            return await self._bulk_delete_files(operation.file_ids, user_id)
        elif operation.operation == "move":
            if not operation.target_path:
                raise ValidationError("Target path is required for move operation")
            return await self._bulk_move_files(operation.file_ids, operation.target_path, user_id)
        else:
            raise ValidationError(f"Unsupported bulk operation: {operation.operation}")

    async def get_file_history(self, file_id: str, user_id: str, limit: int = 10) -> List[Dict[str, any]]:
        """Get file change history (placeholder for future implementation)."""
        # Check if user has access to the file
        await self.get_file(file_id, user_id)  # This will check permissions
        
        # TODO: Implement file history tracking
        # For now, return empty list
        return []

    async def restore_file(self, file_id: str, user_id: str) -> ProjectFileSchema:
        """Restore a deleted file."""
        # Get the deleted file
        query = (
            select(ProjectFile)
            .where(
                and_(
                    ProjectFile.id == UUID(file_id),
                    ProjectFile.is_deleted == True
                )
            )
        )
        
        result = await self.db.execute(query)
        db_file = result.scalar_one_or_none()
        
        if not db_file:
            raise NotFoundError("Deleted file not found")
        
        # Check if user has access to the project
        if not await self.project_service._user_can_edit_project(str(db_file.project_id), user_id):
            raise PermissionError("You don't have permission to restore this file")
        
        # Check if a file already exists at the same path
        existing_query = (
            select(ProjectFile)
            .where(
                and_(
                    ProjectFile.project_id == db_file.project_id,
                    ProjectFile.path == db_file.path,
                    ProjectFile.is_deleted == False
                )
            )
        )
        
        existing_result = await self.db.execute(existing_query)
        if existing_result.scalar_one_or_none():
            raise ValidationError("A file already exists at this path")
        
        # Restore file
        update_query = (
            update(ProjectFile)
            .where(ProjectFile.id == UUID(file_id))
            .values(
                is_deleted=False,
                updated_at=datetime.utcnow(),
                last_modified_by=UUID(user_id)
            )
        )
        
        await self.db.execute(update_query)
        await self.db.commit()
        
        # Update project last activity
        await self._update_project_activity(str(db_file.project_id))
        
        return self._convert_to_schema(db_file)

    # Private helper methods
    async def _update_project_activity(self, project_id: str):
        """Update project's last activity timestamp."""
        update_query = (
            update(Project)
            .where(Project.id == UUID(project_id))
            .values(last_activity=datetime.utcnow())
        )
        
        await self.db.execute(update_query)
        await self.db.commit()

    def _convert_to_schema(self, db_file: ProjectFile) -> ProjectFileSchema:
        """Convert database model to schema."""
        return ProjectFileSchema(
            id=str(db_file.id),
            project_id=str(db_file.project_id),
            name=db_file.name,
            path=db_file.path,
            content=db_file.content,
            file_type=FileType(db_file.file_type),
            size=db_file.size,
            is_deleted=db_file.is_deleted,
            version=db_file.version,
            created_by=str(db_file.created_by),
            created_at=db_file.created_at,
            updated_at=db_file.updated_at,
            last_modified_by=str(db_file.last_modified_by) if db_file.last_modified_by else None
        )

    async def _bulk_delete_files(self, file_ids: List[str], user_id: str) -> Dict[str, int]:
        """Bulk delete files."""
        # Convert string IDs to UUIDs
        uuid_ids = [UUID(file_id) for file_id in file_ids]
        
        # Soft delete files
        update_query = (
            update(ProjectFile)
            .where(
                and_(
                    ProjectFile.id.in_(uuid_ids),
                    ProjectFile.is_deleted == False
                )
            )
            .values(
                is_deleted=True,
                updated_at=datetime.utcnow(),
                last_modified_by=UUID(user_id)
            )
        )
        
        result = await self.db.execute(update_query)
        await self.db.commit()
        
        return {"deleted": result.rowcount, "failed": len(file_ids) - result.rowcount}

    async def _bulk_move_files(self, file_ids: List[str], target_path: str, user_id: str) -> Dict[str, int]:
        """Bulk move files to a new path."""
        # Convert string IDs to UUIDs
        uuid_ids = [UUID(file_id) for file_id in file_ids]
        
        # Get files to move
        query = (
            select(ProjectFile)
            .where(
                and_(
                    ProjectFile.id.in_(uuid_ids),
                    ProjectFile.is_deleted == False
                )
            )
        )
        
        result = await self.db.execute(query)
        files_to_move = result.scalars().all()
        
        moved_count = 0
        for db_file in files_to_move:
            # Create new path
            new_path = f"{target_path.rstrip('/')}/{db_file.name}"
            
            # Check if target path already exists
            existing_query = (
                select(ProjectFile)
                .where(
                    and_(
                        ProjectFile.project_id == db_file.project_id,
                        ProjectFile.path == new_path,
                        ProjectFile.is_deleted == False
                    )
                )
            )
            
            existing_result = await self.db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                continue  # Skip this file if target exists
            
            # Update file path
            update_query = (
                update(ProjectFile)
                .where(ProjectFile.id == db_file.id)
                .values(
                    path=new_path,
                    updated_at=datetime.utcnow(),
                    last_modified_by=UUID(user_id)
                )
            )
            
            await self.db.execute(update_query)
            moved_count += 1
        
        await self.db.commit()
        
        return {"moved": moved_count, "failed": len(file_ids) - moved_count}