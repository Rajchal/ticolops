"""Tests for deployment executor and monitoring functionality."""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deployment_executor import (
    DeploymentExecutor, DeploymentMonitor, DockerExecutor,
    VercelClient, NetlifyClient
)
from app.models.deployment import Deployment, DeploymentStatus, ProjectType
from app.models.repository import Repository, GitProvider
from app.models.project import Project
from app.core.exceptions import DeploymentError


class TestDockerExecutor:
    """Test Docker-based deployment execution."""
    
    @pytest.fixture
    def docker_executor(self):
        """Create Docker executor instance."""
        return DockerExecutor()
    
    @pytest.fixture
    def sample_deployment(self):
        """Create sample deployment for testing."""
        return Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123def456",
            branch="main",
            status=DeploymentStatus.BUILDING.value,
            project_type=ProjectType.REACT.value,
            build_config={
                "build_command": "npm run build",
                "output_directory": "build"
            },
            environment_variables={
                "NODE_ENV": "production",
                "API_URL": "https://api.example.com"
            }
        )
    
    @pytest.fixture
    def sample_repository(self):
        """Create sample repository for testing."""
        return Repository(
            id="repo-123",
            project_id="project-456",
            name="test-repo",
            url="https://github.com/owner/test-repo",
            provider=GitProvider.GITHUB,
            branch="main"
        )
    
    def test_generate_dockerfile_react(self, docker_executor, sample_deployment):
        """Test Dockerfile generation for React project."""
        dockerfile = docker_executor._generate_dockerfile(
            sample_deployment,
            ProjectType.REACT,
            "node:18-alpine"
        )
        
        assert "FROM node:18-alpine" in dockerfile
        assert "ENV NODE_ENV=production" in dockerfile
        assert "ENV API_URL=https://api.example.com" in dockerfile
        assert "RUN npm ci --only=production" in dockerfile
        assert "RUN npm run build" in dockerfile
        assert "FROM nginx:alpine" in dockerfile
        assert "COPY --from=0 /app/build /usr/share/nginx/html" in dockerfile
    
    def test_generate_dockerfile_python(self, docker_executor):
        """Test Dockerfile generation for Python project."""
        deployment = Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.BUILDING.value,
            project_type=ProjectType.FLASK.value,
            build_config={},
            environment_variables={"FLASK_ENV": "production"}
        )
        
        dockerfile = docker_executor._generate_dockerfile(
            deployment,
            ProjectType.FLASK,
            "python:3.11-slim"
        )
        
        assert "FROM python:3.11-slim" in dockerfile
        assert "ENV FLASK_ENV=production" in dockerfile
        assert "RUN pip install --no-cache-dir -r requirements.txt" in dockerfile
        assert "CMD [\"python\", \"app.py\"]" in dockerfile
    
    def test_generate_dockerfile_static(self, docker_executor):
        """Test Dockerfile generation for static project."""
        deployment = Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.BUILDING.value,
            project_type=ProjectType.STATIC.value,
            build_config={},
            environment_variables={}
        )
        
        dockerfile = docker_executor._generate_dockerfile(
            deployment,
            ProjectType.STATIC,
            "nginx:alpine"
        )
        
        assert "FROM nginx:alpine" in dockerfile
        assert "COPY . /usr/share/nginx/html" in dockerfile
        assert "CMD [\"nginx\", \"-g\", \"daemon off;\"]" in dockerfile
    
    @pytest.mark.asyncio
    async def test_build_project_success(self, docker_executor, sample_deployment, sample_repository):
        """Test successful Docker build."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock successful Docker build
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.stdout.readline.side_effect = [
                    b"Step 1/5 : FROM node:18-alpine\n",
                    b"Step 2/5 : WORKDIR /app\n",
                    b"Successfully built abc123\n",
                    b""  # End of output
                ]
                mock_subprocess.return_value = mock_process
                
                success, logs, error = await docker_executor.build_project(
                    sample_deployment, sample_repository, temp_dir
                )
                
                assert success is True
                assert "Successfully built abc123" in logs
                assert error == ""
    
    @pytest.mark.asyncio
    async def test_build_project_failure(self, docker_executor, sample_deployment, sample_repository):
        """Test failed Docker build."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock failed Docker build
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 1
                mock_process.stdout.readline.side_effect = [
                    b"Step 1/5 : FROM node:18-alpine\n",
                    b"ERROR: Build failed\n",
                    b""  # End of output
                ]
                mock_subprocess.return_value = mock_process
                
                success, logs, error = await docker_executor.build_project(
                    sample_deployment, sample_repository, temp_dir
                )
                
                assert success is False
                assert "ERROR: Build failed" in logs
                assert "Docker build failed with exit code 1" in error


class TestHostingPlatformClients:
    """Test hosting platform integrations."""
    
    @pytest.fixture
    def vercel_client(self):
        """Create Vercel client instance."""
        return VercelClient("test-token")
    
    @pytest.fixture
    def netlify_client(self):
        """Create Netlify client instance."""
        return NetlifyClient("test-token")
    
    @pytest.fixture
    def sample_deployment(self):
        """Create sample deployment for testing."""
        return Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.DEPLOYING.value,
            project_type=ProjectType.REACT.value
        )
    
    def test_get_vercel_framework(self, vercel_client):
        """Test Vercel framework mapping."""
        assert vercel_client._get_vercel_framework(ProjectType.REACT.value) == "create-react-app"
        assert vercel_client._get_vercel_framework(ProjectType.NEXTJS.value) == "nextjs"
        assert vercel_client._get_vercel_framework(ProjectType.VUE.value) == "vue"
        assert vercel_client._get_vercel_framework(ProjectType.ANGULAR.value) == "angular"
        assert vercel_client._get_vercel_framework("unknown") is None
    
    @pytest.mark.asyncio
    async def test_vercel_deploy_success(self, vercel_client, sample_deployment):
        """Test successful Vercel deployment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock build files
            os.makedirs(os.path.join(temp_dir, "build"))
            with open(os.path.join(temp_dir, "build", "index.html"), 'w') as f:
                f.write("<h1>Test App</h1>")
            
            # Mock successful Vercel API response
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json.return_value = {"url": "test-app-abc123.vercel.app"}
                mock_post.return_value.__aenter__.return_value = mock_response
                
                success, logs, preview_url = await vercel_client.deploy(sample_deployment, temp_dir)
                
                assert success is True
                assert "Deployed to Vercel" in logs
                assert preview_url == "https://test-app-abc123.vercel.app"
    
    @pytest.mark.asyncio
    async def test_vercel_deploy_failure(self, vercel_client, sample_deployment):
        """Test failed Vercel deployment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock failed Vercel API response
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_response = AsyncMock()
                mock_response.status = 400
                mock_response.text.return_value = "Invalid deployment configuration"
                mock_post.return_value.__aenter__.return_value = mock_response
                
                success, logs, preview_url = await vercel_client.deploy(sample_deployment, temp_dir)
                
                assert success is False
                assert "Vercel deployment failed" in logs
                assert preview_url is None
    
    @pytest.mark.asyncio
    async def test_netlify_deploy_success(self, netlify_client, sample_deployment):
        """Test successful Netlify deployment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock build files
            with open(os.path.join(temp_dir, "index.html"), 'w') as f:
                f.write("<h1>Test App</h1>")
            
            # Mock successful Netlify API responses
            with patch('aiohttp.ClientSession.post') as mock_post:
                # Mock site creation response
                site_response = AsyncMock()
                site_response.status = 201
                site_response.json.return_value = {"id": "site-123"}
                
                # Mock deployment response
                deploy_response = AsyncMock()
                deploy_response.status = 200
                deploy_response.json.return_value = {"deploy_ssl_url": "https://test-app.netlify.app"}
                
                mock_post.return_value.__aenter__.side_effect = [site_response, deploy_response]
                
                success, logs, preview_url = await netlify_client.deploy(sample_deployment, temp_dir)
                
                assert success is True
                assert "Deployed to Netlify" in logs
                assert preview_url == "https://test-app.netlify.app"


@pytest.mark.asyncio
class TestDeploymentExecutor:
    """Test main deployment executor functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def deployment_executor(self, mock_db):
        """Create deployment executor instance."""
        return DeploymentExecutor(mock_db)
    
    @pytest.fixture
    def sample_deployment(self):
        """Create sample deployment for testing."""
        return Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123def456",
            branch="main",
            status=DeploymentStatus.PENDING.value,
            project_type=ProjectType.REACT.value,
            build_config={
                "build_command": "npm run build",
                "output_directory": "build"
            }
        )
    
    @pytest.fixture
    def sample_repository(self):
        """Create sample repository for testing."""
        return Repository(
            id="repo-123",
            project_id="project-456",
            name="test-repo",
            url="https://github.com/owner/test-repo",
            provider=GitProvider.GITHUB,
            branch="main"
        )
    
    async def test_execute_deployment_success(self, deployment_executor, sample_deployment, sample_repository):
        """Test successful deployment execution."""
        # Mock deployment service methods
        with patch.object(deployment_executor.deployment_service, 'get_deployment', return_value=sample_deployment):
            with patch.object(deployment_executor.deployment_service, 'update_deployment_status') as mock_update:
                # Mock database query for repository
                deployment_executor.db.execute = AsyncMock()
                deployment_executor.db.execute.return_value.scalar_one_or_none.return_value = sample_repository
                
                # Mock deployment steps
                with patch.object(deployment_executor, '_clone_repository', return_value="/tmp/test"):
                    with patch.object(deployment_executor, '_build_project', return_value=(True, "Build successful", "")):
                        with patch.object(deployment_executor, '_deploy_to_platform', return_value=(True, "Deploy successful", "https://preview.example.com")):
                            with patch.object(deployment_executor, '_cleanup_source'):
                                
                                await deployment_executor.execute_deployment("deployment-123")
                
                # Verify status updates were called
                assert mock_update.call_count >= 3  # BUILDING, DEPLOYING, SUCCESS
                
                # Check final call was for SUCCESS
                final_call = mock_update.call_args_list[-1]
                assert final_call[1]["status"] == DeploymentStatus.SUCCESS
                assert "preview_url" in final_call[1]
    
    async def test_execute_deployment_build_failure(self, deployment_executor, sample_deployment, sample_repository):
        """Test deployment execution with build failure."""
        # Mock deployment service methods
        with patch.object(deployment_executor.deployment_service, 'get_deployment', return_value=sample_deployment):
            with patch.object(deployment_executor.deployment_service, 'update_deployment_status') as mock_update:
                # Mock database query for repository
                deployment_executor.db.execute = AsyncMock()
                deployment_executor.db.execute.return_value.scalar_one_or_none.return_value = sample_repository
                
                # Mock deployment steps with build failure
                with patch.object(deployment_executor, '_clone_repository', return_value="/tmp/test"):
                    with patch.object(deployment_executor, '_build_project', return_value=(False, "Build failed", "npm error")):
                        with patch.object(deployment_executor, '_cleanup_source'):
                            
                            await deployment_executor.execute_deployment("deployment-123")
                
                # Verify final status was FAILED
                final_call = mock_update.call_args_list[-1]
                assert final_call[1]["status"] == DeploymentStatus.FAILED
                assert "error_message" in final_call[1]
    
    async def test_execute_deployment_repository_not_found(self, deployment_executor, sample_deployment):
        """Test deployment execution with missing repository."""
        # Mock deployment service methods
        with patch.object(deployment_executor.deployment_service, 'get_deployment', return_value=sample_deployment):
            with patch.object(deployment_executor.deployment_service, 'update_deployment_status') as mock_update:
                # Mock repository not found
                deployment_executor.db.execute = AsyncMock()
                deployment_executor.db.execute.return_value.scalar_one_or_none.return_value = None
                
                await deployment_executor.execute_deployment("deployment-123")
                
                # Verify final status was FAILED
                final_call = mock_update.call_args_list[-1]
                assert final_call[1]["status"] == DeploymentStatus.FAILED
                assert "Repository" in final_call[1]["error_message"]
    
    async def test_create_mock_react_project(self, deployment_executor):
        """Test creating mock React project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await deployment_executor._create_mock_react_project(temp_dir)
            
            # Verify package.json was created
            package_json_path = os.path.join(temp_dir, "package.json")
            assert os.path.exists(package_json_path)
            
            # Verify content
            with open(package_json_path, 'r') as f:
                import json
                package_data = json.load(f)
                assert "react" in package_data["dependencies"]
                assert "build" in package_data["scripts"]
    
    async def test_create_mock_python_project(self, deployment_executor):
        """Test creating mock Python project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await deployment_executor._create_mock_python_project(temp_dir)
            
            # Verify files were created
            assert os.path.exists(os.path.join(temp_dir, "requirements.txt"))
            assert os.path.exists(os.path.join(temp_dir, "app.py"))
            
            # Verify content
            with open(os.path.join(temp_dir, "requirements.txt"), 'r') as f:
                content = f.read()
                assert "flask" in content
    
    async def test_build_node_project_success(self, deployment_executor, sample_deployment):
        """Test successful Node.js project build."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create package.json
            package_json = {"scripts": {"build": "echo 'build complete'"}}
            with open(os.path.join(temp_dir, "package.json"), 'w') as f:
                import json
                json.dump(package_json, f)
            
            # Mock successful npm commands
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.stdout.readline.side_effect = [
                    b"npm install complete\n",
                    b""  # End of output
                ]
                mock_subprocess.return_value = mock_process
                
                success, logs, error = await deployment_executor._build_node_project(
                    sample_deployment, temp_dir
                )
                
                assert success is True
                assert "npm install complete" in logs
                assert error == ""
    
    async def test_build_python_project_success(self, deployment_executor, sample_deployment):
        """Test successful Python project build."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create requirements.txt
            with open(os.path.join(temp_dir, "requirements.txt"), 'w') as f:
                f.write("flask==2.3.0\n")
            
            # Mock successful pip install
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.returncode = 0
                mock_process.stdout.readline.side_effect = [
                    b"Successfully installed flask-2.3.0\n",
                    b""  # End of output
                ]
                mock_subprocess.return_value = mock_process
                
                success, logs, error = await deployment_executor._build_python_project(
                    sample_deployment, temp_dir
                )
                
                assert success is True
                assert "Successfully installed flask-2.3.0" in logs
                assert error == ""
    
    async def test_build_static_project(self, deployment_executor, sample_deployment):
        """Test static project build (no build needed)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            success, logs, error = await deployment_executor._build_static_project(
                sample_deployment, temp_dir
            )
            
            assert success is True
            assert "no build required" in logs
            assert error == ""
    
    async def test_deploy_to_platform_mock(self, deployment_executor, sample_deployment):
        """Test mock deployment to platform."""
        with tempfile.TemporaryDirectory() as temp_dir:
            success, logs, preview_url = await deployment_executor._deploy_to_platform(
                sample_deployment, temp_dir
            )
            
            assert success is True
            assert "Deployed successfully" in logs
            assert preview_url.startswith("https://preview-")
            assert "ticolops.dev" in preview_url


@pytest.mark.asyncio
class TestDeploymentMonitor:
    """Test deployment monitoring functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def deployment_monitor(self, mock_db):
        """Create deployment monitor instance."""
        return DeploymentMonitor(mock_db)
    
    async def test_monitor_active_deployments(self, deployment_monitor):
        """Test monitoring active deployments."""
        from datetime import datetime, timedelta
        
        # Mock active deployments
        mock_deployments = [
            Deployment(
                id="deployment-1",
                repository_id="repo-123",
                project_id="project-456",
                commit_sha="abc123",
                branch="main",
                status=DeploymentStatus.BUILDING.value,
                started_at=datetime.utcnow() - timedelta(minutes=5)
            ),
            Deployment(
                id="deployment-2",
                repository_id="repo-456",
                project_id="project-789",
                commit_sha="def456",
                branch="main",
                status=DeploymentStatus.PENDING.value,
                started_at=datetime.utcnow() - timedelta(hours=1)  # Stuck deployment
            )
        ]
        
        # Mock database query
        deployment_monitor.db.execute = AsyncMock()
        deployment_monitor.db.execute.return_value.scalars.return_value.all.return_value = mock_deployments
        
        # Mock deployment service update for stuck deployment
        with patch.object(deployment_monitor.deployment_service, 'update_deployment_status') as mock_update:
            status_updates = await deployment_monitor.monitor_active_deployments()
        
        assert len(status_updates) >= 2
        
        # Check that stuck deployment was marked as failed
        mock_update.assert_called_once()
        timeout_call = mock_update.call_args_list[0]
        assert timeout_call[1]["status"] == DeploymentStatus.FAILED
        assert "timeout" in timeout_call[1]["error_message"]
    
    async def test_collect_deployment_metrics(self, deployment_monitor):
        """Test collecting deployment metrics."""
        # Mock database queries for metrics
        deployment_monitor.db.execute = AsyncMock()
        
        # Mock query results
        total_result = AsyncMock()
        total_result.scalar.return_value = 100
        
        success_result = AsyncMock()
        success_result.scalar.return_value = 85
        
        avg_duration_result = AsyncMock()
        avg_duration_result.scalar.return_value = 120.5
        
        # Set up execute return values
        deployment_monitor.db.execute.side_effect = [
            total_result,
            success_result,
            avg_duration_result
        ]
        
        metrics = await deployment_monitor.collect_deployment_metrics(24)
        
        assert metrics["period_hours"] == 24
        assert metrics["total_deployments"] == 100
        assert metrics["successful_deployments"] == 85
        assert metrics["failed_deployments"] == 15
        assert metrics["success_rate_percent"] == 85.0
        assert metrics["average_duration_seconds"] == 120.5
        assert "collected_at" in metrics
    
    async def test_collect_deployment_metrics_no_data(self, deployment_monitor):
        """Test collecting metrics with no deployment data."""
        # Mock empty database queries
        deployment_monitor.db.execute = AsyncMock()
        
        empty_result = AsyncMock()
        empty_result.scalar.return_value = 0
        
        deployment_monitor.db.execute.return_value = empty_result
        
        metrics = await deployment_monitor.collect_deployment_metrics(24)
        
        assert metrics["total_deployments"] == 0
        assert metrics["successful_deployments"] == 0
        assert metrics["failed_deployments"] == 0
        assert metrics["success_rate_percent"] == 0
        assert metrics["average_duration_seconds"] == 0