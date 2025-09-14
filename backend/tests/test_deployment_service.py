"""Tests for deployment service functionality."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deployment import DeploymentService, ProjectTypeDetector
from app.models.deployment import Deployment, DeploymentStatus, DeploymentTrigger, ProjectType
from app.models.repository import Repository, GitProvider
from app.models.project import Project
from app.core.exceptions import NotFoundError, ValidationError


class TestProjectTypeDetector:
    """Test project type detection functionality."""
    
    @pytest.fixture
    def detector(self):
        """Create project type detector instance."""
        return ProjectTypeDetector()
    
    @pytest.mark.asyncio
    async def test_detect_react_project(self, detector):
        """Test React project detection."""
        files = ["package.json", "src/App.js", "src/index.js", "public/index.html"]
        package_json = {
            "dependencies": {
                "react": "^18.0.0",
                "react-dom": "^18.0.0"
            },
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build"
            }
        }
        
        project_type, confidence, detected_files = await detector.detect_project_type(
            files, package_json
        )
        
        assert project_type == ProjectType.REACT
        assert confidence >= 0.8
        assert "package.json:react" in detected_files
        assert "package.json:react-dom" in detected_files
    
    @pytest.mark.asyncio
    async def test_detect_nextjs_project(self, detector):
        """Test Next.js project detection."""
        files = ["package.json", "next.config.js", "pages/index.js"]
        package_json = {
            "dependencies": {
                "next": "^13.0.0",
                "react": "^18.0.0"
            },
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start"
            }
        }
        
        project_type, confidence, detected_files = await detector.detect_project_type(
            files, package_json
        )
        
        assert project_type == ProjectType.NEXTJS
        assert confidence >= 0.9
        assert "package.json:next" in detected_files
    
    @pytest.mark.asyncio
    async def test_detect_django_project(self, detector):
        """Test Django project detection."""
        files = ["requirements.txt", "manage.py", "settings.py"]
        requirements = "django==4.2.0\npsycopg2-binary==2.9.0"
        
        project_type, confidence, detected_files = await detector.detect_project_type(
            files, requirements_txt_content=requirements
        )
        
        assert project_type == ProjectType.DJANGO
        assert confidence >= 0.9
        assert "requirements.txt:django" in detected_files
    
    @pytest.mark.asyncio
    async def test_detect_unknown_project(self, detector):
        """Test unknown project type detection."""
        files = ["README.md", "LICENSE"]
        
        project_type, confidence, detected_files = await detector.detect_project_type(files)
        
        assert project_type == ProjectType.UNKNOWN
        assert confidence < 0.5
    
    def test_get_build_config_react(self, detector):
        """Test getting build config for React."""
        config = detector.get_build_config(ProjectType.REACT)
        
        assert config["build_command"] == "npm run build"
        assert config["output_directory"] == "build"
        assert config["install_command"] == "npm install"
        assert config["node_version"] == "18"
    
    def test_get_build_config_python(self, detector):
        """Test getting build config for Python."""
        config = detector.get_build_config(ProjectType.PYTHON)
        
        assert config["build_command"] == "pip install -r requirements.txt"
        assert config["output_directory"] == "."
        assert config["python_version"] == "3.11"


@pytest.mark.asyncio
class TestDeploymentService:
    """Test deployment service functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def deployment_service(self, mock_db):
        """Create deployment service instance."""
        return DeploymentService(mock_db)
    
    @pytest.fixture
    def sample_repository(self):
        """Create sample repository for testing."""
        return Repository(
            id="repo-123",
            project_id="project-456",
            name="test-repo",
            url="https://github.com/owner/test-repo",
            provider=GitProvider.GITHUB,
            branch="main",
            deployment_config={
                "auto_deploy": True,
                "build_command": "npm run build",
                "output_directory": "build",
                "environment_variables": {"NODE_ENV": "production"}
            },
            is_active=True
        )
    
    @pytest.fixture
    def sample_project(self):
        """Create sample project for testing."""
        return Project(
            id="project-456",
            name="Test Project",
            description="Test project description",
            owner_id="user-789"
        )
    
    async def test_create_deployment(self, deployment_service, sample_repository, sample_project):
        """Test creating a new deployment."""
        # Mock database queries
        deployment_service.db.execute = AsyncMock()
        deployment_service.db.execute.return_value.scalar_one_or_none.return_value = sample_repository
        deployment_service.db.add = AsyncMock()
        deployment_service.db.commit = AsyncMock()
        deployment_service.db.refresh = AsyncMock()
        
        # Mock the async deployment execution
        with patch.object(deployment_service, '_execute_deployment') as mock_execute:
            mock_execute.return_value = None
            
            deployment = await deployment_service.create_deployment(
                repository_id="repo-123",
                commit_sha="abc123def456",
                branch="main",
                trigger=DeploymentTrigger.PUSH
            )
        
        # Verify deployment creation
        deployment_service.db.add.assert_called_once()
        deployment_service.db.commit.assert_called_once()
        deployment_service.db.refresh.assert_called_once()
    
    async def test_create_deployment_repository_not_found(self, deployment_service):
        """Test creating deployment with non-existent repository."""
        # Mock repository not found
        deployment_service.db.execute = AsyncMock()
        deployment_service.db.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(NotFoundError):
            await deployment_service.create_deployment(
                repository_id="nonexistent",
                commit_sha="abc123",
                branch="main"
            )
    
    async def test_get_deployment(self, deployment_service):
        """Test getting deployment by ID."""
        mock_deployment = Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.SUCCESS.value
        )
        
        # Mock database query
        deployment_service.db.execute = AsyncMock()
        deployment_service.db.execute.return_value.scalar_one_or_none.return_value = mock_deployment
        
        deployment = await deployment_service.get_deployment("deployment-123")
        
        assert deployment.id == "deployment-123"
        assert deployment.status == DeploymentStatus.SUCCESS.value
    
    async def test_get_deployment_not_found(self, deployment_service):
        """Test getting non-existent deployment."""
        # Mock deployment not found
        deployment_service.db.execute = AsyncMock()
        deployment_service.db.execute.return_value.scalar_one_or_none.return_value = None
        
        with pytest.raises(NotFoundError):
            await deployment_service.get_deployment("nonexistent")
    
    async def test_update_deployment_status(self, deployment_service):
        """Test updating deployment status."""
        mock_deployment = Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.BUILDING.value,
            started_at=datetime.utcnow()
        )
        
        # Mock get_deployment
        with patch.object(deployment_service, 'get_deployment', return_value=mock_deployment):
            deployment_service.db.commit = AsyncMock()
            deployment_service.db.refresh = AsyncMock()
            
            updated_deployment = await deployment_service.update_deployment_status(
                deployment_id="deployment-123",
                status=DeploymentStatus.SUCCESS,
                preview_url="https://preview.example.com"
            )
        
        assert updated_deployment.status == DeploymentStatus.SUCCESS.value
        assert updated_deployment.preview_url == "https://preview.example.com"
        assert updated_deployment.completed_at is not None
        deployment_service.db.commit.assert_called_once()
    
    async def test_cancel_deployment(self, deployment_service):
        """Test cancelling an active deployment."""
        mock_deployment = Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.BUILDING.value
        )
        
        # Mock get_deployment
        with patch.object(deployment_service, 'get_deployment', return_value=mock_deployment):
            deployment_service.db.commit = AsyncMock()
            deployment_service.db.refresh = AsyncMock()
            
            cancelled_deployment = await deployment_service.cancel_deployment("deployment-123")
        
        assert cancelled_deployment.status == DeploymentStatus.CANCELLED.value
        assert cancelled_deployment.completed_at is not None
    
    async def test_cancel_deployment_not_active(self, deployment_service):
        """Test cancelling a non-active deployment."""
        mock_deployment = Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.SUCCESS.value
        )
        
        # Mock get_deployment
        with patch.object(deployment_service, 'get_deployment', return_value=mock_deployment):
            with pytest.raises(ValidationError):
                await deployment_service.cancel_deployment("deployment-123")
    
    async def test_get_repository_deployments(self, deployment_service):
        """Test getting deployments for a repository."""
        mock_deployments = [
            Deployment(
                id="deployment-1",
                repository_id="repo-123",
                project_id="project-456",
                commit_sha="abc123",
                branch="main",
                status=DeploymentStatus.SUCCESS.value
            ),
            Deployment(
                id="deployment-2",
                repository_id="repo-123",
                project_id="project-456",
                commit_sha="def456",
                branch="main",
                status=DeploymentStatus.FAILED.value
            )
        ]
        
        # Mock database query
        deployment_service.db.execute = AsyncMock()
        deployment_service.db.execute.return_value.scalars.return_value.all.return_value = mock_deployments
        
        deployments = await deployment_service.get_repository_deployments("repo-123")
        
        assert len(deployments) == 2
        assert deployments[0].id == "deployment-1"
        assert deployments[1].id == "deployment-2"
    
    async def test_get_project_deployments(self, deployment_service):
        """Test getting deployments for a project."""
        mock_deployments = [
            Deployment(
                id="deployment-1",
                repository_id="repo-123",
                project_id="project-456",
                commit_sha="abc123",
                branch="main",
                status=DeploymentStatus.SUCCESS.value
            )
        ]
        
        # Mock database query
        deployment_service.db.execute = AsyncMock()
        deployment_service.db.execute.return_value.scalars.return_value.all.return_value = mock_deployments
        
        deployments = await deployment_service.get_project_deployments("project-456")
        
        assert len(deployments) == 1
        assert deployments[0].project_id == "project-456"
    
    async def test_trigger_deployment_from_webhook(self, deployment_service, sample_repository):
        """Test triggering deployment from webhook."""
        # Mock repository lookup
        deployment_service.db.execute = AsyncMock()
        deployment_service.db.execute.return_value.scalar_one_or_none.return_value = sample_repository
        
        # Mock create_deployment
        mock_deployment = Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.PENDING.value
        )
        
        with patch.object(deployment_service, 'create_deployment', return_value=mock_deployment):
            deployment = await deployment_service.trigger_deployment_from_webhook(
                repository_id="repo-123",
                commit_sha="abc123",
                branch="main",
                pusher_info={"name": "testuser", "email": "test@example.com"}
            )
        
        assert deployment is not None
        assert deployment.id == "deployment-123"
    
    async def test_trigger_deployment_from_webhook_auto_deploy_disabled(self, deployment_service, sample_repository):
        """Test webhook deployment trigger with auto-deploy disabled."""
        # Disable auto-deploy
        sample_repository.deployment_config = {"auto_deploy": False}
        
        # Mock repository lookup
        deployment_service.db.execute = AsyncMock()
        deployment_service.db.execute.return_value.scalar_one_or_none.return_value = sample_repository
        
        deployment = await deployment_service.trigger_deployment_from_webhook(
            repository_id="repo-123",
            commit_sha="abc123",
            branch="main"
        )
        
        assert deployment is None
    
    async def test_trigger_deployment_from_webhook_wrong_branch(self, deployment_service, sample_repository):
        """Test webhook deployment trigger for non-tracked branch."""
        # Repository tracks 'main' branch
        sample_repository.branch = "main"
        
        # Mock repository lookup
        deployment_service.db.execute = AsyncMock()
        deployment_service.db.execute.return_value.scalar_one_or_none.return_value = sample_repository
        
        deployment = await deployment_service.trigger_deployment_from_webhook(
            repository_id="repo-123",
            commit_sha="abc123",
            branch="develop"  # Different branch
        )
        
        assert deployment is None
    
    async def test_get_deployment_stats(self, deployment_service):
        """Test getting deployment statistics."""
        # Mock database queries for stats
        deployment_service.db.execute = AsyncMock()
        
        # Mock total count
        total_result = AsyncMock()
        total_result.scalar.return_value = 100
        
        # Mock status counts
        status_result = AsyncMock()
        status_result.fetchall.return_value = [
            (DeploymentStatus.SUCCESS.value, 80),
            (DeploymentStatus.FAILED.value, 15),
            (DeploymentStatus.BUILDING.value, 5)
        ]
        
        # Mock trigger counts
        trigger_result = AsyncMock()
        trigger_result.fetchall.return_value = [
            (DeploymentTrigger.PUSH.value, 90),
            (DeploymentTrigger.MANUAL.value, 10)
        ]
        
        # Mock duration averages
        duration_result = AsyncMock()
        duration_result.fetchone.return_value = (120.5, 45.2)
        
        # Mock recent deployments
        recent_result = AsyncMock()
        recent_result.scalars.return_value.all.return_value = []
        
        # Set up execute return values in order
        deployment_service.db.execute.side_effect = [
            total_result,
            status_result,
            trigger_result,
            duration_result,
            recent_result
        ]
        
        stats = await deployment_service.get_deployment_stats()
        
        assert stats["total_deployments"] == 100
        assert stats["successful_deployments"] == 80
        assert stats["failed_deployments"] == 15
        assert stats["active_deployments"] == 5
        assert stats["average_build_time_seconds"] == 120.5
        assert stats["average_deployment_time_seconds"] == 45.2
        assert stats["deployments_by_status"][DeploymentStatus.SUCCESS.value] == 80
        assert stats["deployments_by_trigger"][DeploymentTrigger.PUSH.value] == 90
    
    async def test_execute_deployment_success(self, deployment_service):
        """Test successful deployment execution."""
        deployment_id = "deployment-123"
        
        # Mock update_deployment_status calls
        with patch.object(deployment_service, 'update_deployment_status') as mock_update:
            mock_update.return_value = AsyncMock()
            
            await deployment_service._execute_deployment(deployment_id)
        
        # Verify status updates were called
        assert mock_update.call_count == 3  # BUILDING, DEPLOYING, SUCCESS
        
        # Check the final call was for SUCCESS status
        final_call = mock_update.call_args_list[-1]
        assert final_call[0][1] == DeploymentStatus.SUCCESS
        assert "preview_url" in final_call[1]
    
    async def test_execute_deployment_failure(self, deployment_service):
        """Test deployment execution failure."""
        deployment_id = "deployment-123"
        
        # Mock update_deployment_status to raise exception on second call
        with patch.object(deployment_service, 'update_deployment_status') as mock_update:
            mock_update.side_effect = [AsyncMock(), Exception("Build failed"), AsyncMock()]
            
            await deployment_service._execute_deployment(deployment_id)
        
        # Verify final call was for FAILED status
        final_call = mock_update.call_args_list[-1]
        assert final_call[0][1] == DeploymentStatus.FAILED
        assert "error_message" in final_call[1]