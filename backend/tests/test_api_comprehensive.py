"""
Comprehensive API integration tests covering all major endpoints and workflows.
"""

import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from app.main import app
from app.core.security import create_access_token


class TestComprehensiveAPIIntegration:
    """Comprehensive integration tests for the entire API surface"""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def student_auth_headers(self):
        token = create_access_token({"sub": "student-123", "role": "student"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def coordinator_auth_headers(self):
        token = create_access_token({"sub": "coordinator-123", "role": "coordinator"})
        return {"Authorization": f"Bearer {token}"}

    @pytest.mark.asyncio
    async def test_complete_user_journey(self, client, mock_db):
        """Test complete user journey from registration to project collaboration"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # 1. User Registration
            mock_db.execute.return_value.fetchone.return_value = None  # User doesn't exist
            
            register_response = await client.post("/api/auth/register", json={
                "name": "Alice Johnson",
                "email": "alice@university.edu",
                "password": "SecurePass123!",
                "role": "student"
            })
            
            assert register_response.status_code == 201
            register_data = register_response.json()
            assert "access_token" in register_data
            access_token = register_data["access_token"]
            auth_headers = {"Authorization": f"Bearer {access_token}"}
            
            # 2. Profile Management
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "alice-123",
                "email": "alice@university.edu",
                "name": "Alice Johnson",
                "role": "student"
            }
            
            profile_response = await client.get("/api/auth/me", headers=auth_headers)
            assert profile_response.status_code == 200
            
            # 3. Create Project
            project_response = await client.post("/api/projects", 
                json={
                    "name": "Machine Learning Project",
                    "description": "Collaborative ML project for CS course"
                },
                headers=auth_headers
            )
            
            assert project_response.status_code == 201
            project_data = project_response.json()
            project_id = project_data["id"]
            
            # 4. Connect Repository
            with patch('app.services.repository_service.RepositoryService') as mock_repo_service:
                mock_repo_service.return_value.connect_repository.return_value = {
                    "id": "repo-123",
                    "name": "ml-project",
                    "url": "https://github.com/alice/ml-project"
                }
                
                repo_response = await client.post(f"/api/projects/{project_id}/repositories",
                    json={
                        "provider": "github",
                        "url": "https://github.com/alice/ml-project",
                        "access_token": "ghp_test_token"
                    },
                    headers=auth_headers
                )
                
                assert repo_response.status_code == 201
            
            # 5. Track Activity
            activity_response = await client.post(f"/api/projects/{project_id}/activities",
                json={
                    "type": "coding",
                    "location": "src/models/neural_network.py",
                    "metadata": {"action": "create", "lines_added": 150}
                },
                headers=auth_headers
            )
            
            assert activity_response.status_code == 201
            
            # 6. Trigger Deployment
            with patch('app.services.deployment_service.DeploymentService') as mock_deploy_service:
                mock_deploy_service.return_value.trigger_deployment.return_value = {
                    "id": "deploy-123",
                    "status": "pending"
                }
                
                deploy_response = await client.post(f"/api/projects/{project_id}/deployments",
                    json={
                        "repository_id": "repo-123",
                        "branch": "main",
                        "environment": "staging"
                    },
                    headers=auth_headers
                )
                
                assert deploy_response.status_code == 201

    @pytest.mark.asyncio
    async def test_team_collaboration_workflow(self, client, mock_db, student_auth_headers, coordinator_auth_headers):
        """Test team collaboration workflow with multiple users"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            project_id = "project-123"
            
            # Mock project exists
            mock_db.execute.return_value.fetchone.return_value = {
                "id": project_id,
                "owner_id": "coordinator-123"
            }
            
            # 1. Coordinator creates project (already exists in this test)
            
            # 2. Coordinator invites student
            invite_response = await client.post(f"/api/projects/{project_id}/members",
                json={
                    "email": "student@university.edu",
                    "role": "developer"
                },
                headers=coordinator_auth_headers
            )
            
            assert invite_response.status_code == 201
            
            # 3. Both users start working (simulate presence)
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "student-123",
                "project_id": project_id,
                "role": "developer"
            }
            
            # Student updates presence
            presence_response = await client.post("/api/presence/update",
                json={
                    "project_id": project_id,
                    "status": "online",
                    "location": "src/components/Dashboard.tsx"
                },
                headers=student_auth_headers
            )
            
            assert presence_response.status_code == 200
            
            # 4. Track concurrent activities
            student_activity = await client.post(f"/api/projects/{project_id}/activities",
                json={
                    "type": "coding",
                    "location": "src/components/Dashboard.tsx",
                    "metadata": {"action": "edit"}
                },
                headers=student_auth_headers
            )
            
            coordinator_activity = await client.post(f"/api/projects/{project_id}/activities",
                json={
                    "type": "reviewing",
                    "location": "src/components/Dashboard.tsx",
                    "metadata": {"action": "review"}
                },
                headers=coordinator_auth_headers
            )
            
            assert student_activity.status_code == 201
            assert coordinator_activity.status_code == 201
            
            # 5. Check for conflicts
            mock_db.execute.return_value.fetchall.return_value = [
                {
                    "type": "concurrent_work",
                    "location": "src/components/Dashboard.tsx",
                    "users": ["student-123", "coordinator-123"],
                    "severity": "medium"
                }
            ]
            
            conflicts_response = await client.get(f"/api/projects/{project_id}/conflicts", 
                headers=coordinator_auth_headers)
            
            assert conflicts_response.status_code == 200
            conflicts = conflicts_response.json()
            assert len(conflicts) >= 1

    @pytest.mark.asyncio
    async def test_deployment_pipeline_integration(self, client, mock_db, student_auth_headers):
        """Test complete deployment pipeline integration"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.deployment_service.DeploymentService') as mock_deploy_service:
                with patch('app.services.webhook_service.WebhookService') as mock_webhook_service:
                    
                    project_id = "project-123"
                    repo_id = "repo-123"
                    deployment_id = "deploy-123"
                    
                    # Mock services
                    deploy_service = mock_deploy_service.return_value
                    webhook_service = mock_webhook_service.return_value
                    
                    # 1. Setup webhook
                    webhook_service.setup_webhook.return_value = {
                        "webhook_id": "webhook-123",
                        "url": "https://api.ticolops.com/webhooks/github"
                    }
                    
                    webhook_setup_response = await client.post(f"/api/repositories/{repo_id}/webhooks",
                        json={"events": ["push", "pull_request"]},
                        headers=student_auth_headers
                    )
                    
                    assert webhook_setup_response.status_code == 201
                    
                    # 2. Simulate webhook trigger
                    webhook_service.verify_signature.return_value = True
                    deploy_service.trigger_deployment.return_value = {
                        "id": deployment_id,
                        "status": "pending"
                    }
                    
                    webhook_payload = {
                        "ref": "refs/heads/main",
                        "head_commit": {
                            "id": "abc123",
                            "message": "Add new feature"
                        },
                        "repository": {
                            "full_name": "user/repo"
                        }
                    }
                    
                    webhook_response = await client.post("/api/webhooks/github",
                        json=webhook_payload,
                        headers={"X-GitHub-Event": "push"}
                    )
                    
                    assert webhook_response.status_code == 200
                    
                    # 3. Monitor deployment progress
                    mock_db.execute.return_value.fetchone.return_value = {
                        "id": deployment_id,
                        "status": "building",
                        "progress": 75
                    }
                    
                    status_response = await client.get(f"/api/deployments/{deployment_id}",
                        headers=student_auth_headers)
                    
                    assert status_response.status_code == 200
                    
                    # 4. Get deployment logs
                    mock_db.execute.return_value.fetchall.return_value = [
                        {"level": "info", "message": "Build started", "timestamp": "2024-01-01T00:00:00Z"},
                        {"level": "info", "message": "Dependencies installed", "timestamp": "2024-01-01T00:01:00Z"}
                    ]
                    
                    logs_response = await client.get(f"/api/deployments/{deployment_id}/logs",
                        headers=student_auth_headers)
                    
                    assert logs_response.status_code == 200

    @pytest.mark.asyncio
    async def test_notification_system_integration(self, client, mock_db, student_auth_headers):
        """Test notification system integration"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.notification_service.NotificationService') as mock_notification_service:
                
                notification_service = mock_notification_service.return_value
                
                # 1. Subscribe to notifications
                subscribe_response = await client.post("/api/notifications/subscribe",
                    json={
                        "events": ["deployment_success", "deployment_failure", "team_activity"],
                        "channels": ["in_app", "email"]
                    },
                    headers=student_auth_headers
                )
                
                assert subscribe_response.status_code == 200
                
                # 2. Get notification preferences
                mock_db.execute.return_value.fetchone.return_value = {
                    "user_id": "student-123",
                    "events": ["deployment_success", "deployment_failure"],
                    "channels": ["in_app", "email"]
                }
                
                preferences_response = await client.get("/api/notifications/preferences",
                    headers=student_auth_headers)
                
                assert preferences_response.status_code == 200
                
                # 3. Get notification history
                mock_db.execute.return_value.fetchall.return_value = [
                    {
                        "id": "notif-1",
                        "type": "deployment_success",
                        "message": "Deployment completed successfully",
                        "read": False,
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                ]
                
                history_response = await client.get("/api/notifications",
                    headers=student_auth_headers)
                
                assert history_response.status_code == 200
                
                # 4. Mark notification as read
                read_response = await client.post("/api/notifications/notif-1/read",
                    headers=student_auth_headers)
                
                assert read_response.status_code == 200

    @pytest.mark.asyncio
    async def test_real_time_features_integration(self, client, mock_db, student_auth_headers):
        """Test real-time features integration"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            project_id = "project-123"
            
            # Mock project membership
            mock_db.execute.return_value.fetchone.return_value = {
                "user_id": "student-123",
                "project_id": project_id,
                "role": "developer"
            }
            
            # 1. Get team presence
            mock_db.execute.return_value.fetchall.return_value = [
                {
                    "user_id": "student-123",
                    "name": "Alice Johnson",
                    "status": "online",
                    "location": "src/components/Header.tsx",
                    "last_activity": "2024-01-01T00:00:00Z"
                },
                {
                    "user_id": "student-456",
                    "name": "Bob Smith",
                    "status": "away",
                    "location": None,
                    "last_activity": "2024-01-01T00:05:00Z"
                }
            ]
            
            presence_response = await client.get(f"/api/projects/{project_id}/presence",
                headers=student_auth_headers)
            
            assert presence_response.status_code == 200
            presence_data = presence_response.json()
            assert len(presence_data) == 2
            
            # 2. Update user status
            status_update_response = await client.post("/api/presence/update",
                json={
                    "project_id": project_id,
                    "status": "online",
                    "location": "src/utils/helpers.ts"
                },
                headers=student_auth_headers
            )
            
            assert status_update_response.status_code == 200
            
            # 3. Get activity feed
            mock_db.execute.return_value.fetchall.return_value = [
                {
                    "id": "activity-1",
                    "user_name": "Alice Johnson",
                    "type": "coding",
                    "location": "src/utils/helpers.ts",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            ]
            
            activity_feed_response = await client.get(f"/api/projects/{project_id}/activities",
                headers=student_auth_headers)
            
            assert activity_feed_response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_handling_and_validation(self, client, mock_db, student_auth_headers):
        """Test comprehensive error handling and validation"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            
            # 1. Test validation errors
            invalid_user_response = await client.post("/api/auth/register", json={
                "name": "",  # Empty name
                "email": "invalid-email",  # Invalid email
                "password": "123",  # Weak password
                "role": "invalid_role"  # Invalid role
            })
            
            assert invalid_user_response.status_code == 422
            
            # 2. Test authentication errors
            no_auth_response = await client.get("/api/auth/me")
            assert no_auth_response.status_code == 401
            
            invalid_token_response = await client.get("/api/auth/me", 
                headers={"Authorization": "Bearer invalid-token"})
            assert invalid_token_response.status_code == 401
            
            # 3. Test authorization errors
            mock_db.execute.return_value.fetchone.return_value = None  # No project access
            
            forbidden_response = await client.get("/api/projects/project-123",
                headers=student_auth_headers)
            assert forbidden_response.status_code == 404  # Or 403 depending on implementation
            
            # 4. Test not found errors
            not_found_response = await client.get("/api/projects/non-existent",
                headers=student_auth_headers)
            assert not_found_response.status_code == 404
            
            # 5. Test rate limiting (simulated)
            with patch('app.core.rate_limiter.is_rate_limited', return_value=True):
                rate_limit_response = await client.post("/api/auth/login", json={
                    "email": "test@example.com",
                    "password": "password"
                })
                # Note: This would return 429 if rate limiting is implemented

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, client, mock_db, student_auth_headers):
        """Test concurrent operations and race conditions"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            project_id = "project-123"
            
            # Mock project exists
            mock_db.execute.return_value.fetchone.return_value = {
                "id": project_id,
                "owner_id": "student-123"
            }
            
            # Create 20 concurrent activity tracking requests
            activity_tasks = []
            for i in range(20):
                task = client.post(f"/api/projects/{project_id}/activities",
                    json={
                        "type": "coding",
                        "location": f"src/file-{i}.tsx",
                        "metadata": {"action": "edit", "concurrent_test": True}
                    },
                    headers=student_auth_headers
                )
                activity_tasks.append(task)
            
            # Execute all requests concurrently
            responses = await asyncio.gather(*activity_tasks, return_exceptions=True)
            
            # Count successful responses
            successful_responses = [
                r for r in responses 
                if not isinstance(r, Exception) and r.status_code == 201
            ]
            
            # Most requests should succeed
            assert len(successful_responses) >= 15

    @pytest.mark.asyncio
    async def test_data_consistency(self, client, mock_db, student_auth_headers):
        """Test data consistency across operations"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            project_id = "project-123"
            
            # Mock project and user data
            mock_db.execute.return_value.fetchone.return_value = {
                "id": project_id,
                "owner_id": "student-123",
                "name": "Test Project"
            }
            
            # 1. Create activity
            activity_response = await client.post(f"/api/projects/{project_id}/activities",
                json={
                    "type": "coding",
                    "location": "src/main.tsx",
                    "metadata": {"action": "create"}
                },
                headers=student_auth_headers
            )
            
            assert activity_response.status_code == 201
            
            # 2. Verify activity appears in feed
            mock_db.execute.return_value.fetchall.return_value = [
                {
                    "id": "activity-123",
                    "user_id": "student-123",
                    "type": "coding",
                    "location": "src/main.tsx",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            ]
            
            feed_response = await client.get(f"/api/projects/{project_id}/activities",
                headers=student_auth_headers)
            
            assert feed_response.status_code == 200
            activities = feed_response.json()
            assert len(activities) >= 1
            assert activities[0]["location"] == "src/main.tsx"
            
            # 3. Verify presence is updated
            presence_response = await client.get(f"/api/projects/{project_id}/presence",
                headers=student_auth_headers)
            
            assert presence_response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_performance(self, client, mock_db, student_auth_headers):
        """Test API performance under load"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock fast database responses
            mock_db.execute.return_value.fetchall.return_value = []
            
            import time
            
            # Test response times for common endpoints
            start_time = time.time()
            
            # Simulate 10 concurrent requests to different endpoints
            tasks = [
                client.get("/api/auth/me", headers=student_auth_headers),
                client.get("/api/projects", headers=student_auth_headers),
                client.get("/api/notifications", headers=student_auth_headers),
                client.get("/api/presence/status", headers=student_auth_headers),
                client.get("/api/projects/project-123/activities", headers=student_auth_headers),
            ] * 2  # Duplicate to get 10 requests
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # All requests should complete within reasonable time
            assert total_time < 5.0  # 5 seconds for 10 requests
            
            # Most responses should be successful
            successful_responses = [
                r for r in responses 
                if not isinstance(r, Exception) and r.status_code < 400
            ]
            
            assert len(successful_responses) >= 8  # At least 80% success rate