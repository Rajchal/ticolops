import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app
from app.core.security import create_access_token


class TestDeploymentsIntegration:
    """Integration tests for deployment pipeline endpoints"""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def auth_headers(self):
        token = create_access_token({"sub": "user-123", "role": "student"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_complete_deployment_pipeline(self, client, mock_db, auth_headers):
        """Test complete deployment pipeline from trigger to completion"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.deployment_service.DeploymentService') as mock_deployment_service:
                project_id = "project-123"
                repo_id = "repo-123"
                
                # Mock project and repository exist
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": project_id,
                    "owner_id": "user-123"
                }
                
                # Mock deployment service
                deployment_service = mock_deployment_service.return_value
                deployment_service.trigger_deployment.return_value = {
                    "id": "deploy-123",
                    "status": "pending",
                    "repository_id": repo_id,
                    "branch": "main",
                    "commit_hash": "abc123",
                    "triggered_by": "user-123"
                }
                
                # 1. Trigger deployment
                trigger_response = await client.post(f"/api/projects/{project_id}/deployments",
                    json={
                        "repository_id": repo_id,
                        "branch": "main",
                        "environment": "staging"
                    },
                    headers=auth_headers
                )
                
                assert trigger_response.status_code == 201
                deployment_data = trigger_response.json()
                assert deployment_data["status"] == "pending"
                deployment_id = deployment_data["id"]
                
                # 2. Get deployment status
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": deployment_id,
                    "status": "building",
                    "repository_id": repo_id,
                    "branch": "main",
                    "progress": 50
                }
                
                status_response = await client.get(f"/api/deployments/{deployment_id}", headers=auth_headers)
                
                assert status_response.status_code == 200
                status_data = status_response.json()
                assert status_data["status"] == "building"
                
                # 3. Get deployment logs
                mock_db.execute.return_value.fetchall.return_value = [
                    {
                        "id": "log-1",
                        "level": "info",
                        "message": "Starting build process",
                        "timestamp": "2024-01-01T00:00:00Z"
                    },
                    {
                        "id": "log-2",
                        "level": "info",
                        "message": "Installing dependencies",
                        "timestamp": "2024-01-01T00:01:00Z"
                    }
                ]
                
                logs_response = await client.get(f"/api/deployments/{deployment_id}/logs", headers=auth_headers)
                
                assert logs_response.status_code == 200
                logs_data = logs_response.json()
                assert len(logs_data) == 2
                
                # 4. Cancel deployment
                deployment_service.cancel_deployment.return_value = True
                
                cancel_response = await client.post(f"/api/deployments/{deployment_id}/cancel", headers=auth_headers)
                
                assert cancel_response.status_code == 200

    @pytest.mark.asyncio
    async def test_deployment_webhook_handling(self, client, mock_db, auth_headers):
        """Test webhook-triggered deployment flow"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.webhook_service.WebhookService') as mock_webhook_service:
                # Mock webhook verification
                webhook_service = mock_webhook_service.return_value
                webhook_service.verify_signature.return_value = True
                webhook_service.process_webhook.return_value = {
                    "deployment_id": "deploy-456",
                    "triggered": True
                }
                
                # Simulate GitHub webhook payload
                webhook_payload = {
                    "ref": "refs/heads/main",
                    "head_commit": {
                        "id": "def456",
                        "message": "Fix user authentication bug",
                        "author": {
                            "name": "Jane Doe",
                            "email": "jane@example.com"
                        }
                    },
                    "repository": {
                        "full_name": "user/repo",
                        "clone_url": "https://github.com/user/repo.git"
                    }
                }
                
                webhook_headers = {
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": "sha256=test-signature"
                }
                
                # Send webhook
                webhook_response = await client.post("/api/webhooks/github",
                    json=webhook_payload,
                    headers=webhook_headers
                )
                
                assert webhook_response.status_code == 200
                webhook_data = webhook_response.json()
                assert webhook_data["triggered"] is True

    @pytest.mark.asyncio
    async def test_deployment_rollback(self, client, mock_db, auth_headers):
        """Test deployment rollback functionality"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.deployment_service.DeploymentService') as mock_deployment_service:
                deployment_id = "deploy-123"
                previous_deployment_id = "deploy-122"
                
                # Mock current deployment
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": deployment_id,
                    "status": "success",
                    "project_id": "project-123"
                }
                
                # Mock deployment service
                deployment_service = mock_deployment_service.return_value
                deployment_service.rollback_deployment.return_value = {
                    "id": "deploy-124",
                    "status": "pending",
                    "rollback_from": deployment_id,
                    "rollback_to": previous_deployment_id
                }
                
                # Trigger rollback
                rollback_response = await client.post(f"/api/deployments/{deployment_id}/rollback",
                    json={"target_deployment_id": previous_deployment_id},
                    headers=auth_headers
                )
                
                assert rollback_response.status_code == 201
                rollback_data = rollback_response.json()
                assert rollback_data["rollback_from"] == deployment_id

    @pytest.mark.asyncio
    async def test_deployment_environments(self, client, mock_db, auth_headers):
        """Test deployment to different environments"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.deployment_service.DeploymentService') as mock_deployment_service:
                project_id = "project-123"
                
                # Mock project exists
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": project_id,
                    "owner_id": "user-123"
                }
                
                deployment_service = mock_deployment_service.return_value
                
                # Test deployment to staging
                deployment_service.trigger_deployment.return_value = {
                    "id": "deploy-staging",
                    "environment": "staging",
                    "url": "https://staging.example.com"
                }
                
                staging_response = await client.post(f"/api/projects/{project_id}/deployments",
                    json={
                        "repository_id": "repo-123",
                        "branch": "develop",
                        "environment": "staging"
                    },
                    headers=auth_headers
                )
                
                assert staging_response.status_code == 201
                
                # Test deployment to production
                deployment_service.trigger_deployment.return_value = {
                    "id": "deploy-production",
                    "environment": "production",
                    "url": "https://example.com"
                }
                
                production_response = await client.post(f"/api/projects/{project_id}/deployments",
                    json={
                        "repository_id": "repo-123",
                        "branch": "main",
                        "environment": "production"
                    },
                    headers=auth_headers
                )
                
                assert production_response.status_code == 201

    @pytest.mark.asyncio
    async def test_deployment_configuration(self, client, mock_db, auth_headers):
        """Test deployment configuration management"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            project_id = "project-123"
            repo_id = "repo-123"
            
            # Mock repository exists
            mock_db.execute.return_value.fetchone.return_value = {
                "id": repo_id,
                "project_id": project_id
            }
            
            # 1. Update deployment configuration
            config_response = await client.put(f"/api/repositories/{repo_id}/deployment-config",
                json={
                    "build_command": "npm run build:prod",
                    "output_directory": "build",
                    "environment_variables": {
                        "NODE_ENV": "production",
                        "API_URL": "https://api.example.com"
                    },
                    "auto_deploy": True,
                    "deploy_on_push": True
                },
                headers=auth_headers
            )
            
            assert config_response.status_code == 200
            
            # 2. Get deployment configuration
            get_config_response = await client.get(f"/api/repositories/{repo_id}/deployment-config", headers=auth_headers)
            
            assert get_config_response.status_code == 200
            config_data = get_config_response.json()
            assert config_data["build_command"] == "npm run build:prod"

    @pytest.mark.asyncio
    async def test_deployment_analytics(self, client, mock_db, auth_headers):
        """Test deployment analytics and metrics"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            project_id = "project-123"
            
            # Mock analytics data
            mock_db.execute.return_value.fetchall.return_value = [
                {"date": "2024-01-01", "deployments": 5, "success_rate": 0.8},
                {"date": "2024-01-02", "deployments": 3, "success_rate": 1.0},
                {"date": "2024-01-03", "deployments": 7, "success_rate": 0.85}
            ]
            
            # Get deployment analytics
            analytics_response = await client.get(f"/api/projects/{project_id}/deployments/analytics",
                params={"period": "7d"},
                headers=auth_headers
            )
            
            assert analytics_response.status_code == 200
            analytics_data = analytics_response.json()
            assert "deployment_frequency" in analytics_data
            assert "success_rate" in analytics_data

    @pytest.mark.asyncio
    async def test_deployment_error_handling(self, client, mock_db, auth_headers):
        """Test deployment error scenarios"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.deployment_service.DeploymentService') as mock_deployment_service:
                project_id = "project-123"
                
                # Mock project exists
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": project_id,
                    "owner_id": "user-123"
                }
                
                deployment_service = mock_deployment_service.return_value
                
                # 1. Test deployment failure
                deployment_service.trigger_deployment.side_effect = Exception("Build failed: Missing dependencies")
                
                error_response = await client.post(f"/api/projects/{project_id}/deployments",
                    json={
                        "repository_id": "repo-123",
                        "branch": "main",
                        "environment": "staging"
                    },
                    headers=auth_headers
                )
                
                assert error_response.status_code == 500
                
                # 2. Test invalid repository
                mock_db.execute.return_value.fetchone.return_value = None
                
                invalid_repo_response = await client.post(f"/api/projects/{project_id}/deployments",
                    json={
                        "repository_id": "invalid-repo",
                        "branch": "main",
                        "environment": "staging"
                    },
                    headers=auth_headers
                )
                
                assert invalid_repo_response.status_code == 404

    @pytest.mark.asyncio
    async def test_concurrent_deployments(self, client, mock_db, auth_headers):
        """Test handling of concurrent deployment requests"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.deployment_service.DeploymentService') as mock_deployment_service:
                project_id = "project-123"
                
                # Mock project exists
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": project_id,
                    "owner_id": "user-123"
                }
                
                deployment_service = mock_deployment_service.return_value
                deployment_service.trigger_deployment.return_value = {
                    "id": "deploy-concurrent",
                    "status": "pending"
                }
                
                # Create 5 concurrent deployment requests
                deployment_tasks = []
                for i in range(5):
                    task = client.post(f"/api/projects/{project_id}/deployments",
                        json={
                            "repository_id": "repo-123",
                            "branch": f"feature-{i}",
                            "environment": "staging"
                        },
                        headers=auth_headers
                    )
                    deployment_tasks.append(task)
                
                # Execute all requests concurrently
                responses = await asyncio.gather(*deployment_tasks, return_exceptions=True)
                
                # At least one should succeed, others might be queued or rejected
                successful_responses = [r for r in responses if not isinstance(r, Exception) and r.status_code in [201, 202]]
                assert len(successful_responses) >= 1

    @pytest.mark.asyncio
    async def test_deployment_notifications(self, client, mock_db, auth_headers):
        """Test deployment notification system"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.notification_service.NotificationService') as mock_notification_service:
                deployment_id = "deploy-123"
                
                # Mock deployment exists
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": deployment_id,
                    "project_id": "project-123",
                    "triggered_by": "user-123"
                }
                
                notification_service = mock_notification_service.return_value
                
                # Simulate deployment status update
                status_update_response = await client.post(f"/api/deployments/{deployment_id}/status",
                    json={
                        "status": "success",
                        "url": "https://staging.example.com",
                        "duration": 120
                    },
                    headers=auth_headers
                )
                
                assert status_update_response.status_code == 200
                
                # Verify notification was sent
                notification_service.send_deployment_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_deployment_preview_urls(self, client, mock_db, auth_headers):
        """Test deployment preview URL generation and management"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            deployment_id = "deploy-123"
            
            # Mock successful deployment
            mock_db.execute.return_value.fetchone.return_value = {
                "id": deployment_id,
                "status": "success",
                "url": "https://deploy-123.staging.example.com",
                "project_id": "project-123"
            }
            
            # Get deployment preview URL
            preview_response = await client.get(f"/api/deployments/{deployment_id}/preview", headers=auth_headers)
            
            assert preview_response.status_code == 200
            preview_data = preview_response.json()
            assert "url" in preview_data
            assert "expires_at" in preview_data
            
            # Test preview URL access
            url_response = await client.get(preview_data["url"])
            # This would typically redirect or proxy to the actual deployment
            # For testing, we just verify the URL format is correct
            assert preview_data["url"].startswith("https://")

    @pytest.mark.asyncio
    async def test_deployment_security(self, client, mock_db):
        """Test deployment security and access controls"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Test unauthorized access
            unauthorized_response = await client.post("/api/projects/project-123/deployments",
                json={
                    "repository_id": "repo-123",
                    "branch": "main",
                    "environment": "production"
                }
            )
            
            assert unauthorized_response.status_code == 401
            
            # Test access with insufficient permissions
            limited_token = create_access_token({"sub": "user-456", "role": "student"})
            limited_headers = {"Authorization": f"Bearer {limited_token}"}
            
            # Mock user is not project member
            mock_db.execute.return_value.fetchone.return_value = None
            
            forbidden_response = await client.post("/api/projects/project-123/deployments",
                json={
                    "repository_id": "repo-123",
                    "branch": "main",
                    "environment": "production"
                },
                headers=limited_headers
            )
            
            assert forbidden_response.status_code == 403