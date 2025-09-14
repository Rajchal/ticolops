"""Tests for deployment recovery and error handling functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.deployment_recovery import (
    DeploymentRecoveryService, DeploymentErrorAnalyzer, 
    ErrorCategory, ErrorSeverity
)
from app.models.deployment import Deployment, DeploymentStatus, ProjectType
from app.models.repository import Repository, GitProvider
from app.core.exceptions import DeploymentError


class TestDeploymentErrorAnalyzer:
    """Test deployment error analysis functionality."""
    
    @pytest.fixture
    def error_analyzer(self):
        """Create error analyzer instance."""
        return DeploymentErrorAnalyzer()
    
    @pytest.fixture
    def sample_deployment(self):
        """Create sample deployment for testing."""
        return Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.FAILED.value,
            project_type=ProjectType.REACT.value
        )
    
    def test_analyze_build_failure_error(self, error_analyzer, sample_deployment):
        """Test analysis of build failure errors."""
        error_logs = """
        npm ERR! Build failed with exit code 1
        webpack failed to compile
        SyntaxError: Unexpected token in src/App.js
        """
        
        analysis = error_analyzer.analyze_error(error_logs, sample_deployment)
        
        assert analysis["category"] == ErrorCategory.BUILD_FAILURE
        assert analysis["severity"] in [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH]
        assert len(analysis["patterns_matched"]) > 0
        assert len(analysis["suggestions"]) > 0
        assert "build command" in " ".join(analysis["suggestions"]).lower()
    
    def test_analyze_dependency_error(self, error_analyzer, sample_deployment):
        """Test analysis of dependency errors."""
        error_logs = """
        npm ERR! Cannot resolve dependency 'react-router'
        npm ERR! ERESOLVE unable to resolve dependency tree
        Package 'unknown-package' not found
        """
        
        analysis = error_analyzer.analyze_error(error_logs, sample_deployment)
        
        assert analysis["category"] == ErrorCategory.DEPENDENCY_ERROR
        assert len(analysis["patterns_matched"]) > 0
        assert "dependency" in " ".join(analysis["suggestions"]).lower()
    
    def test_analyze_configuration_error(self, error_analyzer, sample_deployment):
        """Test analysis of configuration errors."""
        error_logs = """
        Invalid configuration in webpack.config.js
        Missing environment variable NODE_ENV
        Configuration file not found
        """
        
        analysis = error_analyzer.analyze_error(error_logs, sample_deployment)
        
        assert analysis["category"] == ErrorCategory.CONFIGURATION_ERROR
        assert "configuration" in " ".join(analysis["suggestions"]).lower()
    
    def test_analyze_resource_limit_error(self, error_analyzer, sample_deployment):
        """Test analysis of resource limit errors."""
        error_logs = """
        Out of memory: Kill process 1234
        ENOMEM: not enough memory
        Build timeout after 30 minutes
        """
        
        analysis = error_analyzer.analyze_error(error_logs, sample_deployment)
        
        assert analysis["category"] == ErrorCategory.RESOURCE_LIMIT
        assert analysis["severity"] == ErrorSeverity.HIGH
        assert "memory" in " ".join(analysis["suggestions"]).lower()
    
    def test_analyze_network_error(self, error_analyzer, sample_deployment):
        """Test analysis of network errors."""
        error_logs = """
        Network timeout connecting to registry.npmjs.org
        Connection refused to api.github.com
        DNS resolution failed for example.com
        """
        
        analysis = error_analyzer.analyze_error(error_logs, sample_deployment)
        
        assert analysis["category"] == ErrorCategory.NETWORK_ERROR
        assert "network" in " ".join(analysis["suggestions"]).lower()
    
    def test_analyze_platform_error(self, error_analyzer, sample_deployment):
        """Test analysis of platform errors."""
        error_logs = """
        Platform API error: Service unavailable
        Deployment platform returned 503
        API rate limit exceeded
        """
        
        analysis = error_analyzer.analyze_error(error_logs, sample_deployment)
        
        assert analysis["category"] == ErrorCategory.PLATFORM_ERROR
        assert analysis["severity"] == ErrorSeverity.CRITICAL
        assert "platform" in " ".join(analysis["suggestions"]).lower()
    
    def test_analyze_permission_error(self, error_analyzer, sample_deployment):
        """Test analysis of permission errors."""
        error_logs = """
        Permission denied accessing repository
        Authentication failed for API
        Unauthorized: Invalid credentials
        """
        
        analysis = error_analyzer.analyze_error(error_logs, sample_deployment)
        
        assert analysis["category"] == ErrorCategory.PERMISSION_ERROR
        assert analysis["severity"] == ErrorSeverity.CRITICAL
        assert "permission" in " ".join(analysis["suggestions"]).lower()
    
    def test_analyze_empty_error_logs(self, error_analyzer, sample_deployment):
        """Test analysis with empty error logs."""
        analysis = error_analyzer.analyze_error("", sample_deployment)
        
        assert analysis["category"] == ErrorCategory.UNKNOWN_ERROR
        assert analysis["severity"] == ErrorSeverity.MEDIUM
        assert len(analysis["suggestions"]) > 0
    
    def test_get_quick_fixes_react(self, error_analyzer, sample_deployment):
        """Test getting quick fixes for React project."""
        analysis = error_analyzer.analyze_error("npm ERR! build failed", sample_deployment)
        
        quick_fixes = error_analyzer._get_quick_fixes(ErrorCategory.BUILD_FAILURE, sample_deployment)
        
        assert len(quick_fixes) > 0
        assert any("npm" in fix["command"] for fix in quick_fixes)
    
    def test_get_quick_fixes_python(self, error_analyzer):
        """Test getting quick fixes for Python project."""
        python_deployment = Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.FAILED.value,
            project_type=ProjectType.FLASK.value
        )
        
        quick_fixes = error_analyzer._get_quick_fixes(ErrorCategory.BUILD_FAILURE, python_deployment)
        
        assert len(quick_fixes) > 0
        assert any("pip" in fix["command"] for fix in quick_fixes)
    
    def test_get_related_documentation(self, error_analyzer, sample_deployment):
        """Test getting related documentation."""
        docs = error_analyzer._get_related_documentation(ErrorCategory.BUILD_FAILURE, sample_deployment)
        
        assert len(docs) > 0
        assert all("url" in doc and "title" in doc for doc in docs)


@pytest.mark.asyncio
class TestDeploymentRecoveryService:
    """Test deployment recovery service functionality."""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def recovery_service(self, mock_db):
        """Create recovery service instance."""
        return DeploymentRecoveryService(mock_db)
    
    @pytest.fixture
    def failed_deployment(self):
        """Create failed deployment for testing."""
        return Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123def456",
            branch="main",
            status=DeploymentStatus.FAILED.value,
            project_type=ProjectType.REACT.value,
            build_logs="npm ERR! Build failed",
            deployment_logs="Deployment to platform failed",
            error_message="Build process exited with code 1",
            created_at=datetime.utcnow()
        )
    
    async def test_handle_deployment_failure(self, recovery_service, failed_deployment):
        """Test handling deployment failure analysis."""
        # Mock deployment service
        with patch.object(recovery_service.deployment_service, 'get_deployment', return_value=failed_deployment):
            # Mock recovery options
            with patch.object(recovery_service, '_get_recovery_options', return_value={"retry": True, "rollback_targets": []}):
                with patch.object(recovery_service, '_find_similar_failures', return_value=[]):
                    
                    analysis = await recovery_service.handle_deployment_failure("deployment-123")
        
        assert analysis["deployment_id"] == "deployment-123"
        assert "error_analysis" in analysis
        assert "recovery_options" in analysis
        assert "recovery_plan" in analysis
        assert "auto_retry_recommended" in analysis
        assert "rollback_available" in analysis
    
    async def test_handle_deployment_failure_not_failed(self, recovery_service):
        """Test handling deployment that is not in failed state."""
        successful_deployment = Deployment(
            id="deployment-123",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.SUCCESS.value,
            project_type=ProjectType.REACT.value
        )
        
        with patch.object(recovery_service.deployment_service, 'get_deployment', return_value=successful_deployment):
            with pytest.raises(DeploymentError):
                await recovery_service.handle_deployment_failure("deployment-123")
    
    async def test_auto_retry_deployment_success(self, recovery_service, failed_deployment):
        """Test successful auto-retry of deployment."""
        # Mock deployment service methods
        with patch.object(recovery_service.deployment_service, 'get_deployment', return_value=failed_deployment):
            with patch.object(recovery_service.deployment_service, 'create_deployment') as mock_create:
                with patch.object(recovery_service, '_should_auto_retry', return_value=True):
                    with patch.object(recovery_service, '_get_retry_count', return_value=1):
                        
                        new_deployment = Deployment(
                            id="deployment-456",
                            repository_id="repo-123",
                            project_id="project-456",
                            commit_sha="abc123def456",
                            branch="main",
                            status=DeploymentStatus.PENDING.value,
                            project_type=ProjectType.REACT.value
                        )
                        mock_create.return_value = new_deployment
                        
                        result = await recovery_service.auto_retry_deployment("deployment-123")
        
        assert result is not None
        assert result.id == "deployment-456"
        mock_create.assert_called_once()
    
    async def test_auto_retry_deployment_not_recommended(self, recovery_service, failed_deployment):
        """Test auto-retry when not recommended."""
        with patch.object(recovery_service.deployment_service, 'get_deployment', return_value=failed_deployment):
            with patch.object(recovery_service, '_should_auto_retry', return_value=False):
                
                result = await recovery_service.auto_retry_deployment("deployment-123")
        
        assert result is None
    
    async def test_auto_retry_deployment_max_retries(self, recovery_service, failed_deployment):
        """Test auto-retry when maximum retries reached."""
        with patch.object(recovery_service.deployment_service, 'get_deployment', return_value=failed_deployment):
            with patch.object(recovery_service, '_should_auto_retry', return_value=True):
                with patch.object(recovery_service, '_get_retry_count', return_value=3):  # Max retries
                    
                    result = await recovery_service.auto_retry_deployment("deployment-123")
        
        assert result is None
    
    async def test_rollback_deployment_with_target(self, recovery_service, failed_deployment):
        """Test rollback to specific target deployment."""
        target_deployment = Deployment(
            id="deployment-target",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="previous123",
            branch="main",
            status=DeploymentStatus.SUCCESS.value,
            project_type=ProjectType.REACT.value
        )
        
        rollback_deployment = Deployment(
            id="deployment-rollback",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="previous123",
            branch="main",
            status=DeploymentStatus.PENDING.value,
            project_type=ProjectType.REACT.value
        )
        
        with patch.object(recovery_service.deployment_service, 'get_deployment') as mock_get:
            mock_get.side_effect = [failed_deployment, target_deployment]
            
            with patch.object(recovery_service.deployment_service, 'create_deployment', return_value=rollback_deployment):
                
                result = await recovery_service.rollback_deployment("deployment-123", "deployment-target")
        
        assert result.id == "deployment-rollback"
        assert result.commit_sha == "previous123"
    
    async def test_rollback_deployment_auto_target(self, recovery_service, failed_deployment):
        """Test rollback with automatic target selection."""
        last_successful = Deployment(
            id="deployment-last",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="last123",
            branch="main",
            status=DeploymentStatus.SUCCESS.value,
            project_type=ProjectType.REACT.value
        )
        
        rollback_deployment = Deployment(
            id="deployment-rollback",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="last123",
            branch="main",
            status=DeploymentStatus.PENDING.value,
            project_type=ProjectType.REACT.value
        )
        
        with patch.object(recovery_service.deployment_service, 'get_deployment', return_value=failed_deployment):
            with patch.object(recovery_service, '_find_last_successful_deployment', return_value=last_successful):
                with patch.object(recovery_service.deployment_service, 'create_deployment', return_value=rollback_deployment):
                    
                    result = await recovery_service.rollback_deployment("deployment-123")
        
        assert result.commit_sha == "last123"
    
    async def test_rollback_deployment_no_target(self, recovery_service, failed_deployment):
        """Test rollback when no suitable target found."""
        with patch.object(recovery_service.deployment_service, 'get_deployment', return_value=failed_deployment):
            with patch.object(recovery_service, '_find_last_successful_deployment', return_value=None):
                
                with pytest.raises(DeploymentError):
                    await recovery_service.rollback_deployment("deployment-123")
    
    async def test_get_deployment_health_score(self, recovery_service):
        """Test calculating deployment health score."""
        # Mock recent deployments
        recent_deployments = [
            Deployment(
                id="deployment-1",
                repository_id="repo-123",
                project_id="project-456",
                commit_sha="abc123",
                branch="main",
                status=DeploymentStatus.SUCCESS.value,
                project_type=ProjectType.REACT.value,
                deployment_duration_seconds=120,
                created_at=datetime.utcnow() - timedelta(days=1)
            ),
            Deployment(
                id="deployment-2",
                repository_id="repo-123",
                project_id="project-456",
                commit_sha="def456",
                branch="main",
                status=DeploymentStatus.SUCCESS.value,
                project_type=ProjectType.REACT.value,
                deployment_duration_seconds=150,
                created_at=datetime.utcnow() - timedelta(days=2)
            ),
            Deployment(
                id="deployment-3",
                repository_id="repo-123",
                project_id="project-456",
                commit_sha="ghi789",
                branch="main",
                status=DeploymentStatus.FAILED.value,
                project_type=ProjectType.REACT.value,
                error_message="Build failed",
                created_at=datetime.utcnow() - timedelta(days=3)
            )
        ]
        
        # Mock database query
        recovery_service.db.execute = AsyncMock()
        recovery_service.db.execute.return_value.scalars.return_value.all.return_value = recent_deployments
        
        health_data = await recovery_service.get_deployment_health_score("repo-123")
        
        assert health_data["total_deployments"] == 3
        assert health_data["success_rate"] == 66.67  # 2 out of 3 successful
        assert health_data["avg_duration"] == 135.0  # Average of 120 and 150
        assert health_data["health_score"] >= 60  # Should be reasonable score
        assert len(health_data["failure_trends"]) > 0
        assert len(health_data["recommendations"]) > 0
    
    async def test_get_deployment_health_score_no_data(self, recovery_service):
        """Test health score calculation with no deployment data."""
        # Mock empty database query
        recovery_service.db.execute = AsyncMock()
        recovery_service.db.execute.return_value.scalars.return_value.all.return_value = []
        
        health_data = await recovery_service.get_deployment_health_score("repo-123")
        
        assert health_data["health_score"] == 100  # Perfect score when no data
        assert health_data["total_deployments"] == 0
        assert health_data["success_rate"] == 0
        assert health_data["avg_duration"] == 0
    
    def test_should_auto_retry_network_error(self, recovery_service):
        """Test auto-retry recommendation for network errors."""
        error_analysis = {
            "category": ErrorCategory.NETWORK_ERROR,
            "severity": ErrorSeverity.MEDIUM
        }
        
        should_retry = recovery_service._should_auto_retry(error_analysis)
        assert should_retry is True
    
    def test_should_auto_retry_configuration_error(self, recovery_service):
        """Test auto-retry recommendation for configuration errors."""
        error_analysis = {
            "category": ErrorCategory.CONFIGURATION_ERROR,
            "severity": ErrorSeverity.MEDIUM
        }
        
        should_retry = recovery_service._should_auto_retry(error_analysis)
        assert should_retry is False
    
    def test_should_auto_retry_critical_error(self, recovery_service):
        """Test auto-retry recommendation for critical errors."""
        error_analysis = {
            "category": ErrorCategory.PLATFORM_ERROR,
            "severity": ErrorSeverity.CRITICAL
        }
        
        should_retry = recovery_service._should_auto_retry(error_analysis)
        assert should_retry is False
    
    async def test_get_retry_count(self, recovery_service, failed_deployment):
        """Test getting retry count for a deployment."""
        # Mock deployments with same commit SHA
        same_commit_deployments = [
            failed_deployment,  # Original
            Deployment(id="retry-1", repository_id="repo-123", commit_sha="abc123def456", created_at=datetime.utcnow() - timedelta(minutes=5)),
            Deployment(id="retry-2", repository_id="repo-123", commit_sha="abc123def456", created_at=datetime.utcnow() - timedelta(minutes=10))
        ]
        
        recovery_service.db.execute = AsyncMock()
        recovery_service.db.execute.return_value.scalars.return_value.all.return_value = same_commit_deployments
        
        retry_count = await recovery_service._get_retry_count(failed_deployment)
        
        assert retry_count == 2  # 3 total - 1 original = 2 retries
    
    async def test_find_last_successful_deployment(self, recovery_service):
        """Test finding last successful deployment."""
        successful_deployment = Deployment(
            id="deployment-success",
            repository_id="repo-123",
            project_id="project-456",
            commit_sha="success123",
            branch="main",
            status=DeploymentStatus.SUCCESS.value,
            project_type=ProjectType.REACT.value
        )
        
        recovery_service.db.execute = AsyncMock()
        recovery_service.db.execute.return_value.scalar_one_or_none.return_value = successful_deployment
        
        result = await recovery_service._find_last_successful_deployment("repo-123")
        
        assert result.id == "deployment-success"
        assert result.status == DeploymentStatus.SUCCESS.value
    
    def test_calculate_health_score_perfect(self, recovery_service):
        """Test health score calculation for perfect deployments."""
        score = recovery_service._calculate_health_score(100.0, 60.0, [])
        assert score == 100
    
    def test_calculate_health_score_slow_deployments(self, recovery_service):
        """Test health score calculation with slow deployments."""
        score = recovery_service._calculate_health_score(100.0, 600.0, [])  # 10 minutes
        assert score < 100  # Should be penalized for slow deployments
    
    def test_calculate_health_score_recurring_failures(self, recovery_service):
        """Test health score calculation with recurring failure patterns."""
        failure_trends = [{"category": "build_failure", "percentage": 60}]
        score = recovery_service._calculate_health_score(80.0, 60.0, failure_trends)
        assert score < 80  # Should be penalized for recurring patterns
    
    def test_generate_health_recommendations_low_success(self, recovery_service):
        """Test health recommendations for low success rate."""
        recommendations = recovery_service._generate_health_recommendations(70.0, [])
        assert any("below 80%" in rec for rec in recommendations)
    
    def test_generate_health_recommendations_recurring_failures(self, recovery_service):
        """Test health recommendations for recurring failures."""
        failure_trends = [{"category": "build_failure", "percentage": 40}]
        recommendations = recovery_service._generate_health_recommendations(85.0, failure_trends)
        assert any("build_failure" in rec for rec in recommendations)