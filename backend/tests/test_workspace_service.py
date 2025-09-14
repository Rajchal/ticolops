"""Tests for workspace service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from app.services.workspace import WorkspaceService
from app.schemas.project import ProjectSettings
from app.models.project import Project
from app.models.user import User
from app.core.exceptions import NotFoundError, PermissionError, ValidationError


@pytest.fixture
def mock_db():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def workspace_service(mock_db):
    """Workspace service instance with mocked database."""
    service = WorkspaceService(mock_db)
    # Mock the dependent services
    service.project_service = AsyncMock()
    service.file_service = AsyncMock()
    service.notification_service = AsyncMock()
    return service


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    user = User(
        id=uuid4(),
        email="test@example.com",
        name="Test User",
        hashed_password="hashed_password",
        role="student",
        status="active"
    )
    user.created_at = datetime.utcnow()
    user.updated_at = datetime.utcnow()
    user.last_activity = datetime.utcnow()
    return user


@pytest.fixture
def sample_project():
    """Sample project for testing."""
    project = Project(
        id=uuid4(),
        name="Test Project",
        description="A test project",
        status="active",
        owner_id=uuid4(),
        settings={"auto_save": True, "deployment_enabled": True},
        metadata_info={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        last_activity=datetime.utcnow()
    )
    return project


@pytest.fixture
def project_settings():
    """Sample project settings."""
    return ProjectSettings(
        auto_save=True,
        conflict_resolution="manual",
        deployment_enabled=True,
        public_access=False,
        max_collaborators=10
    )


class TestWorkspaceService:
    """Test cases for WorkspaceService."""

    @pytest.mark.asyncio
    async def test_initialize_member_workspace_success(self, workspace_service, mock_db, sample_user, sample_project):
        """Test successful member workspace initialization."""
        project_id = str(sample_project.id)
        user_id = str(sample_user.id)
        invited_by = str(uuid4())
        
        # Mock project service
        workspace_service.project_service.get_project = AsyncMock(return_value=MagicMock())
        
        # Mock user query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Mock helper methods
        workspace_service._create_default_workspace_structure = AsyncMock(return_value={"user_folder": "/workspace/test_user"})
        workspace_service._setup_user_project_preferences = AsyncMock(return_value={"notifications": {"file_changes": True}})
        workspace_service._create_welcome_activity = AsyncMock(return_value={"type": "member_joined"})
        workspace_service._update_project_activity = AsyncMock()
        
        # Call the method
        result = await workspace_service.initialize_member_workspace(project_id, user_id, invited_by)
        
        # Assertions
        assert result["status"] == "initialized"
        assert "workspace_structure" in result
        assert "user_preferences" in result
        assert "welcome_activity" in result
        workspace_service._update_project_activity.assert_called_once_with(project_id)

    @pytest.mark.asyncio
    async def test_initialize_member_workspace_user_not_found(self, workspace_service, mock_db, sample_project):
        """Test workspace initialization when user doesn't exist."""
        project_id = str(sample_project.id)
        user_id = str(uuid4())
        invited_by = str(uuid4())
        
        # Mock project service
        workspace_service.project_service.get_project = AsyncMock(return_value=MagicMock())
        
        # Mock user query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method and expect NotFoundError
        with pytest.raises(NotFoundError):
            await workspace_service.initialize_member_workspace(project_id, user_id, invited_by)

    @pytest.mark.asyncio
    async def test_update_project_settings_success(self, workspace_service, mock_db, sample_project, project_settings):
        """Test successful project settings update."""
        project_id = str(sample_project.id)
        user_id = str(uuid4())
        
        # Mock permission check
        workspace_service.project_service._user_can_edit_project = AsyncMock(return_value=True)
        
        # Mock project query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        
        # Mock helper methods
        workspace_service._identify_settings_changes = MagicMock(return_value=[{"setting": "auto_save", "old_value": False, "new_value": True}])
        workspace_service.project_service._get_project_members = AsyncMock(return_value=[])
        workspace_service.notification_service.create_settings_change_notification = AsyncMock(return_value=[])
        
        # Call the method
        result = await workspace_service.update_project_settings(project_id, project_settings, user_id)
        
        # Assertions
        assert result["status"] == "updated"
        assert "changes" in result
        assert "notifications_sent" in result
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_project_settings_permission_denied(self, workspace_service, sample_project, project_settings):
        """Test project settings update without permission."""
        project_id = str(sample_project.id)
        user_id = str(uuid4())
        
        # Mock permission check to return False
        workspace_service.project_service._user_can_edit_project = AsyncMock(return_value=False)
        
        # Call the method and expect PermissionError
        with pytest.raises(PermissionError):
            await workspace_service.update_project_settings(project_id, project_settings, user_id)

    @pytest.mark.asyncio
    async def test_update_project_settings_project_not_found(self, workspace_service, mock_db, project_settings):
        """Test project settings update when project doesn't exist."""
        project_id = str(uuid4())
        user_id = str(uuid4())
        
        # Mock permission check
        workspace_service.project_service._user_can_edit_project = AsyncMock(return_value=True)
        
        # Mock project query to return None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        # Call the method and expect NotFoundError
        with pytest.raises(NotFoundError):
            await workspace_service.update_project_settings(project_id, project_settings, user_id)

    @pytest.mark.asyncio
    async def test_get_workspace_overview_success(self, workspace_service, sample_project):
        """Test successful workspace overview retrieval."""
        project_id = str(sample_project.id)
        user_id = str(uuid4())
        
        # Mock permission check
        workspace_service.project_service._user_has_project_access = AsyncMock(return_value=True)
        
        # Mock project service
        workspace_service.project_service.get_project = AsyncMock(return_value=MagicMock())
        
        # Mock helper methods
        workspace_service._get_recent_files = AsyncMock(return_value=[])
        workspace_service._get_user_role_in_project = AsyncMock(return_value="collaborator")
        workspace_service._get_project_activity_summary = AsyncMock(return_value={"total_files": 5})
        workspace_service._get_collaboration_opportunities = AsyncMock(return_value=[])
        
        # Call the method
        result = await workspace_service.get_workspace_overview(project_id, user_id)
        
        # Assertions
        assert result["workspace_ready"] is True
        assert "project" in result
        assert "user_role" in result
        assert "recent_files" in result
        assert "activity_summary" in result
        assert "collaboration_opportunities" in result

    @pytest.mark.asyncio
    async def test_get_workspace_overview_no_access(self, workspace_service, sample_project):
        """Test workspace overview when user has no access."""
        project_id = str(sample_project.id)
        user_id = str(uuid4())
        
        # Mock permission check to return False
        workspace_service.project_service._user_has_project_access = AsyncMock(return_value=False)
        
        # Call the method and expect PermissionError
        with pytest.raises(PermissionError):
            await workspace_service.get_workspace_overview(project_id, user_id)

    @pytest.mark.asyncio
    async def test_setup_project_templates_web_success(self, workspace_service, mock_db, sample_project):
        """Test successful web project template setup."""
        project_id = str(sample_project.id)
        user_id = str(uuid4())
        template_type = "web"
        
        # Mock permission check
        workspace_service.project_service._user_can_edit_project = AsyncMock(return_value=True)
        
        # Mock file service
        workspace_service.file_service.create_file = AsyncMock(return_value=MagicMock())
        
        # Mock project query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        
        # Call the method
        result = await workspace_service.setup_project_templates(project_id, template_type, user_id)
        
        # Assertions
        assert result["template_type"] == "web"
        assert result["status"] == "completed"
        assert result["files_created"] > 0
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_project_templates_invalid_type(self, workspace_service, sample_project):
        """Test project template setup with invalid template type."""
        project_id = str(sample_project.id)
        user_id = str(uuid4())
        template_type = "invalid_template"
        
        # Mock permission check
        workspace_service.project_service._user_can_edit_project = AsyncMock(return_value=True)
        
        # Call the method and expect ValidationError
        with pytest.raises(ValidationError):
            await workspace_service.setup_project_templates(project_id, template_type, user_id)

    @pytest.mark.asyncio
    async def test_setup_project_templates_no_permission(self, workspace_service, sample_project):
        """Test project template setup without permission."""
        project_id = str(sample_project.id)
        user_id = str(uuid4())
        template_type = "web"
        
        # Mock permission check to return False
        workspace_service.project_service._user_can_edit_project = AsyncMock(return_value=False)
        
        # Call the method and expect PermissionError
        with pytest.raises(PermissionError):
            await workspace_service.setup_project_templates(project_id, template_type, user_id)

    @pytest.mark.asyncio
    async def test_manage_member_permissions_success(self, workspace_service, mock_db, sample_project):
        """Test successful member permission management."""
        project_id = str(sample_project.id)
        member_id = str(uuid4())
        user_id = str(uuid4())
        permissions = {"can_edit": True, "can_delete": False}
        
        # Mock permission check
        workspace_service._user_can_manage_permissions = AsyncMock(return_value=True)
        
        # Mock project query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        
        # Call the method
        result = await workspace_service.manage_member_permissions(project_id, member_id, permissions, user_id)
        
        # Assertions
        assert result["status"] == "updated"
        assert result["member_id"] == member_id
        assert result["permissions"] == permissions
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_manage_member_permissions_no_permission(self, workspace_service, sample_project):
        """Test member permission management without permission."""
        project_id = str(sample_project.id)
        member_id = str(uuid4())
        user_id = str(uuid4())
        permissions = {"can_edit": True}
        
        # Mock permission check to return False
        workspace_service._user_can_manage_permissions = AsyncMock(return_value=False)
        
        # Call the method and expect PermissionError
        with pytest.raises(PermissionError):
            await workspace_service.manage_member_permissions(project_id, member_id, permissions, user_id)

    def test_identify_settings_changes(self, workspace_service):
        """Test settings change identification."""
        old_settings = {"auto_save": False, "deployment_enabled": True, "max_collaborators": 5}
        new_settings = {"auto_save": True, "deployment_enabled": True, "max_collaborators": 10}
        
        changes = workspace_service._identify_settings_changes(old_settings, new_settings)
        
        assert len(changes) == 2
        assert any(change["setting"] == "auto_save" for change in changes)
        assert any(change["setting"] == "max_collaborators" for change in changes)

    def test_get_template_config_web(self, workspace_service):
        """Test getting web template configuration."""
        config = workspace_service._get_template_config("web")
        
        assert config is not None
        assert config["version"] == "1.0"
        assert len(config["files"]) == 4  # index.html, styles.css, script.js, README.md

    def test_get_template_config_api(self, workspace_service):
        """Test getting API template configuration."""
        config = workspace_service._get_template_config("api")
        
        assert config is not None
        assert config["version"] == "1.0"
        assert len(config["files"]) == 3  # main.py, requirements.txt, README.md

    def test_get_template_config_invalid(self, workspace_service):
        """Test getting invalid template configuration."""
        config = workspace_service._get_template_config("invalid")
        
        assert config is None