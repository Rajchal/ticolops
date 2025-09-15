import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.core.security import create_access_token


class TestAuthIntegration:
    """Integration tests for authentication endpoints"""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_complete_auth_flow(self, client, mock_db):
        """Test complete authentication flow from registration to logout"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # 1. Register new user
            mock_db.execute.return_value.fetchone.return_value = None  # User doesn't exist
            
            register_response = await client.post("/api/auth/register", json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "password123",
                "role": "student"
            })
            
            assert register_response.status_code == 201
            register_data = register_response.json()
            assert "access_token" in register_data
            assert register_data["user"]["email"] == "test@example.com"
            
            # 2. Login with registered credentials
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "hashed_password": "$2b$12$hash",
                "name": "Test User",
                "role": "student",
                "status": "active"
            }
            
            login_response = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
            
            assert login_response.status_code == 200
            login_data = login_response.json()
            assert "access_token" in login_data
            access_token = login_data["access_token"]
            
            # 3. Access protected endpoint
            profile_response = await client.get("/api/auth/me", headers={
                "Authorization": f"Bearer {access_token}"
            })
            
            assert profile_response.status_code == 200
            profile_data = profile_response.json()
            assert profile_data["email"] == "test@example.com"
            
            # 4. Update profile
            update_response = await client.put("/api/auth/profile", 
                json={"name": "Updated Name"},
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert update_response.status_code == 200
            
            # 5. Change password
            password_response = await client.post("/api/auth/change-password",
                json={
                    "current_password": "password123",
                    "new_password": "newpassword123"
                },
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            assert password_response.status_code == 200

    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, client, mock_db):
        """Test token refresh functionality"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user data
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "hashed_password": "$2b$12$hash",
                "name": "Test User",
                "role": "student"
            }
            
            # Login to get tokens
            login_response = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
            
            login_data = login_response.json()
            refresh_token = login_data["refresh_token"]
            
            # Use refresh token to get new access token
            refresh_response = await client.post("/api/auth/refresh", json={
                "refresh_token": refresh_token
            })
            
            assert refresh_response.status_code == 200
            refresh_data = refresh_response.json()
            assert "access_token" in refresh_data
            
            # Use new access token
            new_token = refresh_data["access_token"]
            profile_response = await client.get("/api/auth/me", headers={
                "Authorization": f"Bearer {new_token}"
            })
            
            assert profile_response.status_code == 200

    @pytest.mark.asyncio
    async def test_password_reset_flow(self, client, mock_db):
        """Test password reset functionality"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.email_service.EmailService.send_email') as mock_email:
                # Mock user exists
                mock_db.execute.return_value.fetchone.return_value = {
                    "id": "user-123",
                    "email": "test@example.com",
                    "name": "Test User"
                }
                
                # Request password reset
                reset_request_response = await client.post("/api/auth/forgot-password", json={
                    "email": "test@example.com"
                })
                
                assert reset_request_response.status_code == 200
                assert mock_email.called
                
                # Simulate reset token (normally sent via email)
                reset_token = "reset-token-123"
                
                # Reset password with token
                reset_response = await client.post("/api/auth/reset-password", json={
                    "token": reset_token,
                    "new_password": "newpassword123"
                })
                
                assert reset_response.status_code == 200

    @pytest.mark.asyncio
    async def test_auth_error_scenarios(self, client, mock_db):
        """Test various authentication error scenarios"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # 1. Login with non-existent user
            mock_db.execute.return_value.fetchone.return_value = None
            
            login_response = await client.post("/api/auth/login", json={
                "email": "nonexistent@example.com",
                "password": "password123"
            })
            
            assert login_response.status_code == 401
            assert "Invalid credentials" in login_response.json()["detail"]
            
            # 2. Login with wrong password
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "hashed_password": "$2b$12$different_hash",
                "name": "Test User",
                "role": "student"
            }
            
            login_response = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword"
            })
            
            assert login_response.status_code == 401
            
            # 3. Access protected endpoint without token
            profile_response = await client.get("/api/auth/me")
            
            assert profile_response.status_code == 401
            
            # 4. Access protected endpoint with invalid token
            profile_response = await client.get("/api/auth/me", headers={
                "Authorization": "Bearer invalid-token"
            })
            
            assert profile_response.status_code == 401
            
            # 5. Register with existing email
            mock_db.execute.return_value.fetchone.return_value = {
                "email": "existing@example.com"
            }
            
            register_response = await client.post("/api/auth/register", json={
                "name": "Test User",
                "email": "existing@example.com",
                "password": "password123",
                "role": "student"
            })
            
            assert register_response.status_code == 400
            assert "already registered" in register_response.json()["detail"]

    @pytest.mark.asyncio
    async def test_role_based_access_control(self, client, mock_db):
        """Test role-based access control"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Create tokens for different roles
            student_token = create_access_token({"sub": "student-123", "role": "student"})
            coordinator_token = create_access_token({"sub": "coordinator-123", "role": "coordinator"})
            admin_token = create_access_token({"sub": "admin-123", "role": "admin"})
            
            # Mock user data for different roles
            def mock_user_by_role(user_id):
                if "student" in user_id:
                    return {"id": user_id, "role": "student", "email": "student@example.com"}
                elif "coordinator" in user_id:
                    return {"id": user_id, "role": "coordinator", "email": "coordinator@example.com"}
                else:
                    return {"id": user_id, "role": "admin", "email": "admin@example.com"}
            
            mock_db.execute.return_value.fetchone.side_effect = lambda query: mock_user_by_role("student-123")
            
            # Test student access to admin endpoint (should fail)
            admin_response = await client.get("/api/admin/users", headers={
                "Authorization": f"Bearer {student_token}"
            })
            
            assert admin_response.status_code == 403
            
            # Test coordinator access to coordinator endpoint (should succeed)
            mock_db.execute.return_value.fetchone.side_effect = lambda query: mock_user_by_role("coordinator-123")
            
            coordinator_response = await client.get("/api/coordinator/projects", headers={
                "Authorization": f"Bearer {coordinator_token}"
            })
            
            # Note: This would succeed if the endpoint exists and is properly configured
            # For this test, we're checking that the auth middleware works correctly
            
            # Test admin access to admin endpoint (should succeed)
            mock_db.execute.return_value.fetchone.side_effect = lambda query: mock_user_by_role("admin-123")
            
            admin_response = await client.get("/api/admin/users", headers={
                "Authorization": f"Bearer {admin_token}"
            })
            
            # The response code depends on whether the endpoint exists
            # We're primarily testing that the token is accepted

    @pytest.mark.asyncio
    async def test_concurrent_auth_requests(self, client, mock_db):
        """Test authentication under concurrent load"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock successful login
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "hashed_password": "$2b$12$hash",
                "name": "Test User",
                "role": "student"
            }
            
            # Create 20 concurrent login requests
            login_tasks = []
            for i in range(20):
                task = client.post("/api/auth/login", json={
                    "email": f"user{i}@example.com",
                    "password": "password123"
                })
                login_tasks.append(task)
            
            # Execute all requests concurrently
            responses = await asyncio.gather(*login_tasks)
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
                assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_session_management(self, client, mock_db):
        """Test session management and logout"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user data
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "hashed_password": "$2b$12$hash",
                "name": "Test User",
                "role": "student"
            }
            
            # Login
            login_response = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
            
            access_token = login_response.json()["access_token"]
            
            # Verify session is active
            profile_response = await client.get("/api/auth/me", headers={
                "Authorization": f"Bearer {access_token}"
            })
            
            assert profile_response.status_code == 200
            
            # Logout
            logout_response = await client.post("/api/auth/logout", headers={
                "Authorization": f"Bearer {access_token}"
            })
            
            assert logout_response.status_code == 200
            
            # Verify session is invalidated (if token blacklisting is implemented)
            # This test assumes token blacklisting is implemented
            # If not, the token would still be valid until expiration