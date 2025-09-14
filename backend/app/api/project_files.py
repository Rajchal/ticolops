"""Project file management API endpoints."""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.project import (
    ProjectFile, ProjectFileCreate, ProjectFileUpdate, FileType,
    BulkFileOperation
)
from app.services.project_file import ProjectFileService
from app.core.exceptions import NotFoundError, PermissionError, ValidationError

router = APIRouter()


@router.post("/projects/{project_id}/files", response_model=ProjectFile, status_code=status.HTTP_201_CREATED)
async def create_file(
    project_id: str,
    file_data: ProjectFileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new file in a project."""
    try:
        file_service = ProjectFileService(db)
        return await file_service.create_file(project_id, file_data, str(current_user.id))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/projects/{project_id}/files", response_model=List[ProjectFile])
async def get_project_files(
    project_id: str,
    file_type: Optional[FileType] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all files in a project."""
    try:
        file_service = ProjectFileService(db)
        return await file_service.get_project_files(project_id, str(current_user.id), file_type)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/files/{file_id}", response_model=ProjectFile)
async def get_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific file by ID."""
    try:
        file_service = ProjectFileService(db)
        return await file_service.get_file(file_id, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/files/{file_id}", response_model=ProjectFile)
async def update_file(
    file_id: str,
    file_data: ProjectFileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a file."""
    try:
        file_service = ProjectFileService(db)
        return await file_service.update_file(file_id, file_data, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a file (soft delete)."""
    try:
        file_service = ProjectFileService(db)
        await file_service.delete_file(file_id, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/files/{file_id}/restore", response_model=ProjectFile)
async def restore_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Restore a deleted file."""
    try:
        file_service = ProjectFileService(db)
        return await file_service.restore_file(file_id, str(current_user.id))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/files/{file_id}/history", response_model=List[Dict[str, Any]])
async def get_file_history(
    file_id: str,
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get file change history."""
    try:
        file_service = ProjectFileService(db)
        return await file_service.get_file_history(file_id, str(current_user.id), limit)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/projects/{project_id}/files/bulk", response_model=Dict[str, int])
async def bulk_file_operation(
    project_id: str,
    operation: BulkFileOperation,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform bulk operations on files."""
    try:
        file_service = ProjectFileService(db)
        return await file_service.bulk_file_operation(project_id, operation, str(current_user.id))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))