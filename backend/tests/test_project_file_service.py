"""Tests for project file service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.project_file import ProjectFileService
from app.schemas.project import ProjectFileCreate, ProjectFileUpdate, FileType, BulkFileOperation
from app.models.project import ProjectFile
from app.models.user import User
from app.core.exceptions import NotFoundError, PermissionError, ValidationError


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def project_file_service(mock_db):
    """Project file service instance with mocked database."""
    service = ProjectFileService(mock_db)
    # Mock the project service dependency
    service.project_service._user_has_project_access = AsyncMock(return_value=True)
    service.project_service._user_can_edit_project = AsyncMock(return_value=True)
    return service


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        hashed_password="hashed_password",
        role="student",
        status="active"
    )


@pytest.fixture
def sample_project_file():
    """Sample project file for testing."""
    return ProjectFile(
        id=uuid4(),
        project_id=uuid4(),
        name="test.html",
        path="/src/test.html",
        content="<html><body>Test</body></html>",
        file_type="html",
        size="32",
        is_deleted=False,
        version="1.0.0",
        created_by=uuid4(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_modified_by=None
    )


@pytest.fixture
def file_create_data():
    """Sample file creation data."""
    return ProjectFileCreate(
        name="index.html",
        path="/src/index.html",
        content="<html><body>Hello World</body></html>",
        file_type=FileType.HTML
    )


class TestProjectFileService:
    """Test cases for ProjectFileService."""

    @pytest.mark.asyncio
    async def test_create_file_success(self, project_file_service, mock_db, sample_user, file_create_data):
        """Test successful file creation."""
        project_id = str(uuid4())
        
        # Mock existing file check (no existing file)
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = None
        
        # Mock database operations
        mock_db.execute = AsyncMock(return_value=mock_existing_result)
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock project activity update
        project_file_service._update_project_activity = AsyncMock()
        
        # Call the method
        result = await project_file_service.create_file(project_id, file_create_data, str(sample_user.id))
        
        # Assertions
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        project_file_service._update_project_activity.assert_called_once_with(project_id)
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_file_already_exists(self, project_file_service, mock_db, sample_user, file_create_data, sample_project_file):
        """Test file creation when file already exists at path."""
        project_id = str(uuid4())
        
        # Mock existing file check (file exists)
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = sample_project_file
        mock_db.execute = AsyncMock(return_value=mock_existing_result)
        
        # Call the method and expect ValidationError
        with pytest.raises(ValidationError):
            await project_file_service.create_file(project_id, file_create_data, str(sample_user.id))

    @pytest.mark.asyncio
    async def test_create_file_no_permission(self, project_file_service, sample_user, file_create_data):
        """Test file creation without project access."""
        project_id = str(uuid4())
        
        # Mock permission check to return False
        project_file_service.project_service._user_has_project_access = AsyncMock(return_value=False)
        
        # Call the method and expect PermissionError
        with pytest.raises(PermissionError):
            await project_file_service.create_file(project_id, file_create_data, str(sample_user.id))

    @pytest.mark.asyncio
    async def test_get_file_success(self, project_file_service, mock_db, sample_user, sample_project_file):
        """Test successful file retrieval."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_file
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method
        result = await project_file_service.get_file(str(sample_project_file.id), str(sample_user.id))
        
        # Assertions
        assert result is not None
        assert result.id == str(sample_project_file.id)
        assert result.name == sample_project_file.name

    @pytest.mark.asyncio
    async def test_get_file_not_found(self, project_file_service, mock_db, sample_user):
        """Test file retrieval when file doesn't exist."""
        # Mock database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method and expect NotFoundError
        with pytest.raises(NotFoundError):
            await project_file_service.get_file(str(uuid4()), str(sample_user.id))

    @pytest.mark.asyncio
    async def test_get_file_no_permission(self, project_file_service, mock_db, sample_user, sample_project_file):
        """Test file retrieval without project access."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_file
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock permission check to return False
        project_file_service.project_service._user_has_project_access = AsyncMock(return_value=False)
        
        # Call the method and expect PermissionError
        with pytest.raises(PermissionError):
            await project_file_service.get_file(str(sample_project_file.id), str(sample_user.id))

    @pytest.mark.asyncio
    async def test_update_file_success(self, project_file_service, mock_db, sample_user, sample_project_file):
        """Test successful file update."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_file
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        
        # Mock get_file for return value
        project_file_service.get_file = AsyncMock(return_value=MagicMock())
        project_file_service._update_project_activity = AsyncMock()
        
        # Create update data
        update_data = ProjectFileUpdate(content="<html><body>Updated</body></html>")
        
        # Call the method
        result = await project_file_service.update_file(str(sample_project_file.id), update_data, str(sample_user.id))
        
        # Assertions
        mock_db.commit.assert_called_once()
        project_file_service._update_project_activity.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_file_path_conflict(self, project_file_service, mock_db, sample_user, sample_project_file):
        """Test file update with path conflict."""
        # Mock database query for file
        mock_file_result = MagicMock()
        mock_file_result.scalar_one_or_none.return_value = sample_project_file
        
        # Mock database query for existing file at new path
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = MagicMock()  # File exists at new path
        
        mock_db.execute = AsyncMock(side_effect=[mock_file_result, mock_existing_result])
        
        # Create update data with new path
        update_data = ProjectFileUpdate(path="/src/new-path.html")
        
        # Call the method and expect ValidationError
        with pytest.raises(ValidationError):
            await project_file_service.update_file(str(sample_project_file.id), update_data, str(sample_user.id))

    @pytest.mark.asyncio
    async def test_delete_file_success(self, project_file_service, mock_db, sample_user, sample_project_file):
        """Test successful file deletion (soft delete)."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project_file
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        
        # Mock project activity update
        project_file_service._update_project_activity = AsyncMock()
        
        # Call the method
        result = await project_file_service.delete_file(str(sample_project_file.id), str(sample_user.id))
        
        # Assertions
        assert result is True
        mock_db.commit.assert_called_once()
        project_file_service._update_project_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_file_not_found(self, project_file_service, mock_db, sample_user):
        """Test file deletion when file doesn't exist."""
        # Mock database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method and expect NotFoundError
        with pytest.raises(NotFoundError):
            await project_file_service.delete_file(str(uuid4()), str(sample_user.id))

    @pytest.mark.asyncio
    async def test_get_project_files(self, project_file_service, mock_db, sample_user):
        """Test getting all files in a project."""
        project_id = str(uuid4())
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method
        result = await project_file_service.get_project_files(project_id, str(sample_user.id))
        
        # Assertions
        assert isinstance(result, list)
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_project_files_with_filter(self, project_file_service, mock_db, sample_user):
        """Test getting project files with file type filter."""
        project_id = str(uuid4())
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method with file type filter
        result = await project_file_service.get_project_files(project_id, str(sample_user.id), FileType.HTML)
        
        # Assertions
        assert isinstance(result, list)
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_delete_files(self, project_file_service, mock_db, sample_user):
        """Test bulk file deletion."""
        project_id = str(uuid4())
        file_ids = [str(uuid4()), str(uuid4())]
        
        # Mock database operation
        mock_result = MagicMock()
        mock_result.rowcount = 2
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        
        # Create bulk operation
        operation = BulkFileOperation(file_ids=file_ids, operation="delete")
        
        # Call the method
        result = await project_file_service.bulk_file_operation(project_id, operation, str(sample_user.id))
        
        # Assertions
        assert result["deleted"] == 2
        assert result["failed"] == 0
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_move_files(self, project_file_service, mock_db, sample_user, sample_project_file):
        """Test bulk file move operation."""
        project_id = str(uuid4())
        file_ids = [str(sample_project_file.id)]
        target_path = "/new-folder"
        
        # Mock database queries
        mock_files_result = MagicMock()
        mock_files_result.scalars.return_value.all.return_value = [sample_project_file]
        
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = None  # No conflict
        
        mock_db.execute = AsyncMock(side_effect=[mock_files_result, mock_existing_result])
        mock_db.commit = AsyncMock()
        
        # Create bulk operation
        operation = BulkFileOperation(file_ids=file_ids, operation="move", target_path=target_path)
        
        # Call the method
        result = await project_file_service.bulk_file_operation(project_id, operation, str(sample_user.id))
        
        # Assertions
        assert result["moved"] == 1
        assert result["failed"] == 0
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_operation_unsupported(self, project_file_service, sample_user):
        """Test bulk operation with unsupported operation type."""
        project_id = str(uuid4())
        file_ids = [str(uuid4())]
        
        # Create bulk operation with unsupported operation
        operation = BulkFileOperation(file_ids=file_ids, operation="unsupported")
        
        # Call the method and expect ValidationError
        with pytest.raises(ValidationError):
            await project_file_service.bulk_file_operation(project_id, operation, str(sample_user.id))

    @pytest.mark.asyncio
    async def test_restore_file_success(self, project_file_service, mock_db, sample_user, sample_project_file):
        """Test successful file restoration."""
        # Set file as deleted
        sample_project_file.is_deleted = True
        
        # Mock database queries
        mock_deleted_result = MagicMock()
        mock_deleted_result.scalar_one_or_none.return_value = sample_project_file
        
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = None  # No file at path
        
        mock_db.execute = AsyncMock(side_effect=[mock_deleted_result, mock_existing_result])
        mock_db.commit = AsyncMock()
        
        # Mock project activity update
        project_file_service._update_project_activity = AsyncMock()
        
        # Call the method
        result = await project_file_service.restore_file(str(sample_project_file.id), str(sample_user.id))
        
        # Assertions
        assert result is not None
        mock_db.commit.assert_called_once()
        project_file_service._update_project_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_file_path_conflict(self, project_file_service, mock_db, sample_user, sample_project_file):
        """Test file restoration with path conflict."""
        # Set file as deleted
        sample_project_file.is_deleted = True
        
        # Mock database queries
        mock_deleted_result = MagicMock()
        mock_deleted_result.scalar_one_or_none.return_value = sample_project_file
        
        mock_existing_result = MagicMock()
        mock_existing_result.scalar_one_or_none.return_value = MagicMock()  # File exists at path
        
        mock_db.execute = AsyncMock(side_effect=[mock_deleted_result, mock_existing_result])
        
        # Call the method and expect ValidationError
        with pytest.raises(ValidationError):
            await project_file_service.restore_file(str(sample_project_file.id), str(sample_user.id))

    @pytest.mark.asyncio
    async def test_get_file_history(self, project_file_service, sample_user, sample_project_file):
        """Test getting file history (placeholder implementation)."""
        # Mock get_file to check permissions
        project_file_service.get_file = AsyncMock(return_value=MagicMock())
        
        # Call the method
        result = await project_file_service.get_file_history(str(sample_project_file.id), str(sample_user.id))
        
        # Assertions (currently returns empty list)
        assert isinstance(result, list)
        assert len(result) == 0