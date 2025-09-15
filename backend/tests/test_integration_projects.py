import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.core.security import create_access_token


class TestProjectsIntegration:
    """Integration tests for project management endpoints"""

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
    async def test_complete_project_lifecycle(self, client, mock_db, auth_headers):
        """Test complete project lifecycle from creation to deletion"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user data
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "role": "student"
            }
            
            # 1. Create project
            create_response = await client.post("/api/projects", 
                json={
                    "name": "Test Project",
                    "description": "A test project for integration testing"
                },
                headers=auth_headers
            )
            
            assert create_response.status_code == 201
            project_data = create_response.json()
            assert project_data["name"] == "Test Project"
            project_id = project_data["id"]
            
            # 2. Get project details
            mock_db.execute.return_value.fetchone.return_value = {
                "id": project_id,
                "name": "Test Project",
                "description": "A test project for integration testing",
                "owner_id": "user-123",
                "created_at": "2024-01-01T00:00:00Z"
            }
            
            get_response = await client.get(f"/api/projects/{project_id}", headers=auth_headers)
            
            assert get_response.status_code == 200
            get_data = get_response.json()
            assert get_data["name"] == "Test Project"
            
            # 3. Update project
            update_response = await client.put(f"/api/projects/{project_id}",
                json={
                    "name": "Updated Test Project",
                    "description": "Updated description"
                },
                headers=auth_headers
            )
            
            assert update_response.status_code == 200
            
            # 4. List projects
            mock_db.execute.return_value.fetchall.return_value = [
                {
                    "id": project_id,
                    "name": "Updated Test Project",
                    "description": "Updated description",
                    "owner_id": "user-123"
                }
            ]
            
            list_response = await client.get("/api/projects", headers=auth_headers)
            
            assert list_response.status_code == 200
            projects = list_response.json()
            assert len(projects) >= 1
            assert any(p["id"] == project_id for p in projects)
            
            # 5. Delete project
            delete_response = await client.delete(f"/api/projects/{project_id}", headers=auth_headers)
            
            assert delete_response.status_code == 204

    @pytest.mark.asyncio
    async def test_project_team_management(self, client, mock_db, auth_headers):
        """Test project team management functionality"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            project_id = "project-123"
            
            # Mock project exists and user is owner
            mock_db.execute.return_value.fetchone.return_value = {
                "id": project_id,
                "owner_id": "user-123"
            }
            
            # 1. Invite team member
            invite_response = await client.post(f"/api/projects/{project_id}/members",
                json={
                    "email": "teammate@example.com",
                    "role": "developer"
                },
                headers=auth_headers
            )
            
            assert invite_response.status_code == 201
            
            # 2. List team members
            mock_db.execute.return_value.fetchall.return_value = [
                {
                    "user_id": "user-123",
                    "email": "test@example.com",
                    "name": "Test User",
                    "role": "owner"
                },
                {
                    "user_id": "user-456",
                    "email": "teammate@example.com",
                    "name": "Teammate",
                    "role": "developer"
                }
            ]
            
            members_response = await client.get(f"/api/projects/{project_id}/members", headers=auth_headers)
            
            assert members_response.status_code == 200
            members = members_response.json()
            assert len(members) == 2
            
            # 3. Update member role
            update_role_response = await client.put(f"/api/projects/{project_id}/members/user-456",
                json={"role": "maintainer"},
                headers=auth_headers
            )
            
            assert update_role_response.status_code == 200
            
            # 4. Remove team member
            remove_response = await client.delete(f"/api/projects/{project_id}/members/user-456", headers=auth_headers)
            
            assert remove_response.status_code == 204

    @pytest.mark.asyncio
    async def test_project_repository_integration(self, client, mock_db, auth_headers):
        """Test project repository integration"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.repository_service.RepositoryService') as mock_repo_service:
                project_id = "project-123"
                
                # Mock project exists
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": project_id,
                    "owner_id": "user-123"
                }
                
                # Mock repository service
                mock_repo_service.return_value.connect_repository.return_value = {
                    "id": "repo-123",
                    "name": "test-repo",
                    "url": "https://github.com/user/test-repo",
                    "provider": "github"
                }
                
                # 1. Connect repository
                connect_response = await client.post(f"/api/projects/{project_id}/repositories",
                    json={
                        "provider": "github",
                        "url": "https://github.com/user/test-repo",
                        "access_token": "ghp_test_token"
                    },
                    headers=auth_headers
                )
                
                assert connect_response.status_code == 201
                repo_data = connect_response.json()
                assert repo_data["url"] == "https://github.com/user/test-repo"
                
                # 2. List repositories
                mock_db.execute.return_value.fetchall.return_value = [
                    {
                        "id": "repo-123",
                        "name": "test-repo",
                        "url": "https://github.com/user/test-repo",
                        "provider": "github",
                        "branch": "main"
                    }
                ]
                
                repos_response = await client.get(f"/api/projects/{project_id}/repositories", headers=auth_headers)
                
                assert repos_response.status_code == 200
                repos = repos_response.json()
                assert len(repos) >= 1
                
                # 3. Update repository settings
                update_response = await client.put(f"/api/projects/{project_id}/repositories/repo-123",
                    json={
                        "branch": "develop",
                        "auto_deploy": True
                    },
                    headers=auth_headers
                )
                
                assert update_response.status_code == 200
                
                # 4. Disconnect repository
                disconnect_response = await client.delete(f"/api/projects/{project_id}/repositories/repo-123", headers=auth_headers)
                
                assert disconnect_response.status_code == 204

    @pytest.mark.asyncio
    async def test_project_activities_tracking(self, client, mock_db, auth_headers):
        """Test project activity tracking"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            project_id = "project-123"
            
            # Mock project exists
            mock_db.execute.return_value.fetchone.return_value = {
                "id": project_id,
                "owner_id": "user-123"
            }
            
            # 1. Create activity
            activity_response = await client.post(f"/api/projects/{project_id}/activities",
                json={
                    "type": "coding",
                    "location": "src/components/Header.tsx",
                    "metadata": {"action": "edit", "lines_changed": 15}
                },
                headers=auth_headers
            )
            
            assert activity_response.status_code == 201
            
            # 2. Get activity feed
            mock_db.execute.return_value.fetchall.return_value = [
                {
                    "id": "activity-123",
                    "user_id": "user-123",
                    "user_name": "Test User",
                    "type": "coding",
                    "location": "src/components/Header.tsx",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "metadata": {"action": "edit", "lines_changed": 15}
                }
            ]
            
            feed_response = await client.get(f"/api/projects/{project_id}/activities", headers=auth_headers)
            
            assert feed_response.status_code == 200
            activities = feed_response.json()
            assert len(activities) >= 1
            assert activities[0]["type"] == "coding"
            
            # 3. Get user activities
            user_activities_response = await client.get(f"/api/projects/{project_id}/activities/user/user-123", headers=auth_headers)
            
            assert user_activities_response.status_code == 200
            
            # 4. Get activity analytics
            mock_db.execute.return_value.fetchall.return_value = [
                {"type": "coding", "count": 25},
                {"type": "reviewing", "count": 10},
                {"type": "testing", "count": 5}
            ]
            
            analytics_response = await client.get(f"/api/projects/{project_id}/activities/analytics", headers=auth_headers)
            
            assert analytics_response.status_code == 200
            analytics = analytics_response.json()
            assert "activity_by_type" in analytics

    @pytest.mark.asyncio
    async def test_project_permissions(self, client, mock_db):
        """Test project permission system"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            project_id = "project-123"
            
            # Create tokens for different users
            owner_token = create_access_token({"sub": "owner-123", "role": "student"})
            member_token = create_access_token({"sub": "member-123", "role": "student"})
            outsider_token = create_access_token({"sub": "outsider-123", "role": "student"})
            
            owner_headers = {"Authorization": f"Bearer {owner_token}"}
            member_headers = {"Authorization": f"Bearer {member_token}"}
            outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
            
            # Mock project with different user permissions
            def mock_project_access(user_id):
                if user_id == "owner-123":
                    return {"id": project_id, "owner_id": "owner-123", "role": "owner"}
                elif user_id == "member-123":
                    return {"id": project_id, "owner_id": "owner-123", "role": "developer"}
                else:
                    return None
            
            # 1. Owner can access project
            mock_db.execute.return_value.fetchone.side_effect = lambda query: mock_project_access("owner-123")
            
            owner_response = await client.get(f"/api/projects/{project_id}", headers=owner_headers)
            assert owner_response.status_code == 200
            
            # 2. Member can access project (read-only)
            mock_db.execute.return_value.fetchone.side_effect = lambda query: mock_project_access("member-123")
            
            member_response = await client.get(f"/api/projects/{project_id}", headers=member_headers)
            assert member_response.status_code == 200
            
            # 3. Member cannot delete project
            delete_response = await client.delete(f"/api/projects/{project_id}", headers=member_headers)
            assert delete_response.status_code == 403
            
            # 4. Outsider cannot access project
            mock_db.execute.return_value.fetchone.side_effect = lambda query: mock_project_access("outsider-123")
            
            outsider_response = await client.get(f"/api/projects/{project_id}", headers=outsider_headers)
            assert outsider_response.status_code == 404  # Or 403, depending on implementation

    @pytest.mark.asyncio
    async def test_project_search_and_filtering(self, client, mock_db, auth_headers):
        """Test project search and filtering functionality"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock search results
            mock_db.execute.return_value.fetchall.return_value = [
                {
                    "id": "project-1",
                    "name": "React Project",
                    "description": "A React-based web application",
                    "owner_id": "user-123"
                },
                {
                    "id": "project-2",
                    "name": "Node.js API",
                    "description": "Backend API built with Node.js",
                    "owner_id": "user-456"
                }
            ]
            
            # 1. Search projects by name
            search_response = await client.get("/api/projects?search=React", headers=auth_headers)
            
            assert search_response.status_code == 200
            projects = search_response.json()
            assert len(projects) >= 1
            
            # 2. Filter projects by owner
            filter_response = await client.get("/api/projects?owner_id=user-123", headers=auth_headers)
            
            assert filter_response.status_code == 200
            
            # 3. Paginate results
            paginated_response = await client.get("/api/projects?page=1&limit=10", headers=auth_headers)
            
            assert paginated_response.status_code == 200
            
            # 4. Sort projects
            sorted_response = await client.get("/api/projects?sort_by=created_at&order=desc", headers=auth_headers)
            
            assert sorted_response.status_code == 200

    @pytest.mark.asyncio
    async def test_project_error_handling(self, client, mock_db, auth_headers):
        """Test project error handling scenarios"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # 1. Get non-existent project
            mock_db.execute.return_value.fetchone.return_value = None
            
            get_response = await client.get("/api/projects/non-existent", headers=auth_headers)
            
            assert get_response.status_code == 404
            
            # 2. Create project with invalid data
            invalid_response = await client.post("/api/projects",
                json={"name": ""},  # Empty name
                headers=auth_headers
            )
            
            assert invalid_response.status_code == 422
            
            # 3. Update project without permission
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "project-123",
                "owner_id": "different-user"
            }
            
            update_response = await client.put("/api/projects/project-123",
                json={"name": "Updated Name"},
                headers=auth_headers
            )
            
            assert update_response.status_code == 403
            
            # 4. Invite member with invalid email
            invite_response = await client.post("/api/projects/project-123/members",
                json={
                    "email": "invalid-email",
                    "role": "developer"
                },
                headers=auth_headers
            )
            
            assert invite_response.status_code == 422

    @pytest.mark.asyncio
    async def test_concurrent_project_operations(self, client, mock_db, auth_headers):
        """Test concurrent project operations"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock successful operations
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "project-123",
                "owner_id": "user-123"
            }
            
            # Create 10 concurrent activity creation requests
            activity_tasks = []
            for i in range(10):
                task = client.post("/api/projects/project-123/activities",
                    json={
                        "type": "coding",
                        "location": f"src/file-{i}.tsx",
                        "metadata": {"action": "edit"}
                    },
                    headers=auth_headers
                )
                activity_tasks.append(task)
            
            # Execute all requests concurrently
            responses = await asyncio.gather(*activity_tasks)
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == 201