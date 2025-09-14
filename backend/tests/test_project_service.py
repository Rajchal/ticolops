"""Tests for project service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from app.services.project import ProjectService
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectStatus, ProjectRole, ProjectSettings
from app.models.project import Project, ProjectStatus as ProjectStatusEnum, ProjectRole as ProjectRoleEnum
from app.models.user import User
from app.core.exceptions import NotFoundError, PermissionError, ValidationError


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def project_service(mock_db):
    """Project service instance with mocked database."""
    return ProjectService(mock_db)


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
def sample_project():
    """Sample project for testing."""
    return Project(
        id=uuid4(),
        name="Test Project",
        description="A test project",
        status=ProjectStatusEnum.ACTIVE.value,
        owner_id=uuid4(),
        settings={"auto_save": True},
        metadata_info={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_activity=datetime.utcnow()
    )


@pytest.fixture
def project_create_data():
    """Sample project creation data."""
    return ProjectCreate(
        name="New Project",
        description="A new test project",
        status=ProjectStatus.ACTIVE,
        settings=ProjectSettings(auto_save=True, deployment_enabled=True),
        metadata_info={"category": "web"}
    )


class TestProjectService:
    """Test cases for ProjectService."""

    @pytest.mark.asyncio
    async def test_create_project_success(self, project_service, mock_db, sample_user, project_create_data):
        """Test successful project creation."""
        # Mock database operations
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        
        # Mock the get_project method to return a project
        project_service.get_project = AsyncMock(return_value=MagicMock())
        project_service._add_project_member = AsyncMock()
        
        # Call the method
        result = await project_service.create_project(project_create_data, str(sample_user.id))
        
        # Assertions
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        project_service._add_project_member.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_get_project_success(self, project_service, mock_db, sample_user, sample_project):
        """Test successful project retrieval."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock permission check
        project_service._user_has_project_access = AsyncMock(return_value=True)
        project_service._get_project_members = AsyncMock(return_value=[])
        
        # Call the method
        result = await project_service.get_project(str(sample_project.id), str(sample_user.id))
        
        # Assertions
        assert result is not None
        assert result.id == str(sample_project.id)
        assert result.name == sample_project.name

    @pytest.mark.asyncio
    async def test_get_project_permission_denied(self, project_service, sample_user, sample_project):
        """Test project retrieval with insufficient permissions."""
        # Mock permission check to return False
        project_service._user_has_project_access = AsyncMock(return_value=False)
        
        # Call the method and expect PermissionError
        with pytest.raises(PermissionError):
            await project_service.get_project(str(sample_project.id), str(sample_user.id))

    @pytest.mark.asyncio
    async def test_get_project_not_found(self, project_service, mock_db, sample_user):
        """Test project retrieval when project doesn't exist."""
        # Mock database query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock permission check
        project_service._user_has_project_access = AsyncMock(return_value=True)
        
        # Call the method and expect NotFoundError
        with pytest.raises(NotFoundError):
            await project_service.get_project(str(uuid4()), str(sample_user.id))

    @pytest.mark.asyncio
    async def test_update_project_success(self, project_service, mock_db, sample_user, sample_project):
        """Test successful project update."""
        # Mock permission check
        project_service._user_can_edit_project = AsyncMock(return_value=True)
        project_service.get_project = AsyncMock(return_value=MagicMock())
        
        # Mock database operations
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Create update data
        update_data = ProjectUpdate(name="Updated Project", description="Updated description")
        
        # Call the method
        result = await project_service.update_project(str(sample_project.id), update_data, str(sample_user.id))
        
        # Assertions
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_project_permission_denied(self, project_service, sample_user, sample_project):
        """Test project update with insufficient permissions."""
        # Mock permission check to return False
        project_service._user_can_edit_project = AsyncMock(return_value=False)
        
        # Create update data
        update_data = ProjectUpdate(name="Updated Project")
        
        # Call the method and expect PermissionError
        with pytest.raises(PermissionError):
            await project_service.update_project(str(sample_project.id), update_data, str(sample_user.id))

    @pytest.mark.asyncio
    async def test_delete_project_success(self, project_service, mock_db, sample_user, sample_project):
        """Test successful project deletion."""
        # Set the project owner to the current user
        sample_project.owner_id = sample_user.id
        
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.delete = AsyncMock()
        mock_db.commit = AsyncMock()
        
        # Call the method
        result = await project_service.delete_project(str(sample_project.id), str(sample_user.id))
        
        # Assertions
        assert result is True
        mock_db.delete.assert_called_once_with(sample_project)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_project_not_owner(self, project_service, mock_db, sample_user, sample_project):
        """Test project deletion when user is not the owner."""
        # Mock database query to return None (user is not owner)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method and expect PermissionError
        with pytest.raises(PermissionError):
            await project_service.delete_project(str(sample_project.id), str(sample_user.id))

    @pytest.mark.asyncio
    async def test_get_user_projects(self, project_service, mock_db, sample_user):
        """Test getting user's projects."""
        # Mock database query
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method
        result = await project_service.get_user_projects(str(sample_user.id))
        
        # Assertions
        assert isinstance(result, list)
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_project_member_success(self, project_service, mock_db, sample_user, sample_project):
        """Test successful project member addition."""
        # Mock permission check
        project_service._user_can_edit_project = AsyncMock(return_value=True)
        project_service._user_has_project_access = AsyncMock(return_value=False)
        project_service._add_project_member = AsyncMock(return_value=MagicMock())
        
        # Mock user lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method
        result = await project_service.add_project_member(
            str(sample_project.id), 
            sample_user.email, 
            ProjectRole.COLLABORATOR, 
            str(uuid4())
        )
        
        # Assertions
        assert result is not None
        project_service._add_project_member.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_project_member_user_not_found(self, project_service, mock_db, sample_project):
        """Test adding project member when user doesn't exist."""
        # Mock permission check
        project_service._user_can_edit_project = AsyncMock(return_value=True)
        
        # Mock user lookup to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method and expect NotFoundError
        with pytest.raises(NotFoundError):
            await project_service.add_project_member(
                str(sample_project.id), 
                "nonexistent@example.com", 
                ProjectRole.COLLABORATOR, 
                str(uuid4())
            )

    @pytest.mark.asyncio
    async def test_add_project_member_already_member(self, project_service, mock_db, sample_user, sample_project):
        """Test adding project member when user is already a member."""
        # Mock permission check
        project_service._user_can_edit_project = AsyncMock(return_value=True)
        project_service._user_has_project_access = AsyncMock(return_value=True)
        
        # Mock user lookup
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method and expect ValidationError
        with pytest.raises(ValidationError):
            await project_service.add_project_member(
                str(sample_project.id), 
                sample_user.email, 
                ProjectRole.COLLABORATOR, 
                str(uuid4())
            )

    @pytest.mark.asyncio
    async def test_remove_project_member_success(self, project_service, mock_db, sample_user, sample_project):
        """Test successful project member removal."""
        # Mock permission check
        project_service._user_can_edit_project = AsyncMock(return_value=True)
        
        # Mock project query (user is not owner)
        mock_result = MagicMock()
        sample_project.owner_id = uuid4()  # Different from user being removed
        mock_result.scalar_one_or_none.return_value = sample_project
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock delete operation
        mock_delete_result = MagicMock()
        mock_delete_result.rowcount = 1
        mock_db.execute = AsyncMock(side_effect=[mock_result, mock_delete_result])
        mock_db.commit = AsyncMock()
        
        # Call the method
        result = await project_service.remove_project_member(
            str(sample_project.id), 
            str(sample_user.id), 
            str(uuid4())
        )
        
        # Assertions
        assert result is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_project_member_cannot_remove_owner(self, project_service, mock_db, sample_user, sample_project):
        """Test that project owner cannot be removed."""
        # Mock permission check
        project_service._user_can_edit_project = AsyncMock(return_value=True)
        
        # Mock project query (user is owner)
        mock_result = MagicMock()
        sample_project.owner_id = sample_user.id
        mock_result.scalar_one_or_none.return_value = sample_project
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method and expect ValidationError
        with pytest.raises(ValidationError):
            await project_service.remove_project_member(
                str(sample_project.id), 
                str(sample_user.id), 
                str(uuid4())
            )

    @pytest.mark.asyncio
    async def test_get_project_stats(self, project_service, mock_db, sample_user, sample_project):
        """Test getting project statistics."""
        # Mock permission check
        project_service._user_has_project_access = AsyncMock(return_value=True)
        
        # Mock database queries for stats
        mock_file_result = MagicMock()
        mock_file_result.first.return_value = MagicMock(total_files=5, total_size=1024, last_modified=datetime.utcnow())
        
        mock_member_result = MagicMock()
        mock_member_result.scalar.return_value = 3
        
        mock_deployment_result = MagicMock()
        mock_deployment_result.scalar.return_value = 2
        
        mock_db.execute = AsyncMock(side_effect=[mock_file_result, mock_member_result, mock_deployment_result])
        
        # Call the method
        result = await project_service.get_project_stats(str(sample_project.id), str(sample_user.id))
        
        # Assertions
        assert result is not None
        assert result.total_files == 5
        assert result.active_collaborators == 3
        assert result.total_deployments == 2