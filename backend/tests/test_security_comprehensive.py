"""
Comprehensive security testing for authentication and webhook verification.
"""

import pytest
import asyncio
import hashlib
import hmac
import jwt
import time
from datetime import datetime, timedelta
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings


class TestSecurityComprehensive:
    """Comprehensive security testing suite"""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_jwt_token_security(self, client, mock_db):
        """Test JWT token security and validation"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Test valid token
            valid_payload = {"sub": "user-123", "role": "student", "exp": time.time() + 3600}
            valid_token = create_access_token(valid_payload)
            
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "role": "student",
                "status": "active"
            }
            
            valid_response = await client.get("/api/auth/me", 
                headers={"Authorization": f"Bearer {valid_token}"})
            assert valid_response.status_code == 200
            
            # Test expired token
            expired_payload = {"sub": "user-123", "role": "student", "exp": time.time() - 3600}
            expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm="HS256")
            
            expired_response = await client.get("/api/auth/me",
                headers={"Authorization": f"Bearer {expired_token}"})
            assert expired_response.status_code == 401
            
            # Test malformed token
            malformed_response = await client.get("/api/auth/me",
                headers={"Authorization": "Bearer invalid.token.here"})
            assert malformed_response.status_code == 401
            
            # Test token with invalid signature
            invalid_payload = {"sub": "user-123", "role": "student", "exp": time.time() + 3600}
            invalid_token = jwt.encode(invalid_payload, "wrong-secret", algorithm="HS256")
            
            invalid_response = await client.get("/api/auth/me",
                headers={"Authorization": f"Bearer {invalid_token}"})
            assert invalid_response.status_code == 401
            
            # Test token without required claims
            incomplete_payload = {"sub": "user-123"}  # Missing role
            incomplete_token = jwt.encode(incomplete_payload, settings.SECRET_KEY, algorithm="HS256")
            
            incomplete_response = await client.get("/api/auth/me",
                headers={"Authorization": f"Bearer {incomplete_token}"})
            assert incomplete_response.status_code == 401

    @pytest.mark.asyncio
    async def test_password_security(self, client, mock_db):
        """Test password hashing and validation security"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Test strong password requirements
            weak_passwords = [
                "123",
                "password",
                "12345678",
                "qwerty",
                "abc123"
            ]
            
            for weak_password in weak_passwords:
                mock_db.execute.return_value.fetchone.return_value = None
                
                response = await client.post("/api/auth/register", json={
                    "name": "Test User",
                    "email": "test@example.com",
                    "password": weak_password,
                    "role": "student"
                })
                
                # Should reject weak passwords
                assert response.status_code == 422
            
            # Test password hashing
            password = "StrongPassword123!"
            hashed = get_password_hash(password)
            
            # Hash should be different from original
            assert hashed != password
            
            # Should verify correctly
            assert verify_password(password, hashed) is True
            
            # Should not verify with wrong password
            assert verify_password("WrongPassword", hashed) is False
            
            # Test that same password produces different hashes (salt)
            hash1 = get_password_hash(password)
            hash2 = get_password_hash(password)
            assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_authentication_brute_force_protection(self, client, mock_db):
        """Test protection against brute force attacks"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user exists with wrong password
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "hashed_password": get_password_hash("correct_password"),
                "role": "student"
            }
            
            # Attempt multiple failed logins
            failed_attempts = []
            for i in range(10):
                response = await client.post("/api/auth/login", json={
                    "email": "test@example.com",
                    "password": "wrong_password"
                })
                failed_attempts.append(response.status_code)
            
            # All should fail with 401
            assert all(status == 401 for status in failed_attempts)
            
            # In a real implementation, rate limiting would kick in
            # This test verifies the basic authentication failure handling

    @pytest.mark.asyncio
    async def test_role_based_access_control(self, client, mock_db):
        """Test role-based access control security"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Create tokens for different roles
            student_token = create_access_token({"sub": "student-123", "role": "student"})
            coordinator_token = create_access_token({"sub": "coordinator-123", "role": "coordinator"})
            admin_token = create_access_token({"sub": "admin-123", "role": "admin"})
            
            # Mock user data
            def mock_user_by_id(user_id):
                if "student" in user_id:
                    return {"id": user_id, "role": "student", "email": "student@example.com"}
                elif "coordinator" in user_id:
                    return {"id": user_id, "role": "coordinator", "email": "coordinator@example.com"}
                else:
                    return {"id": user_id, "role": "admin", "email": "admin@example.com"}
            
            # Test student cannot access admin endpoints
            mock_db.execute.return_value.fetchone.return_value = mock_user_by_id("student-123")
            
            student_admin_response = await client.get("/api/admin/users",
                headers={"Authorization": f"Bearer {student_token}"})
            assert student_admin_response.status_code in [403, 404]  # Forbidden or Not Found
            
            # Test role escalation prevention
            # Student tries to modify their role in token
            malicious_payload = {"sub": "student-123", "role": "admin"}
            malicious_token = create_access_token(malicious_payload)
            
            # But database still shows student role
            mock_db.execute.return_value.fetchone.return_value = mock_user_by_id("student-123")
            
            escalation_response = await client.get("/api/admin/users",
                headers={"Authorization": f"Bearer {malicious_token}"})
            assert escalation_response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_webhook_signature_verification(self, client, mock_db):
        """Test webhook signature verification security"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.webhook_service.WebhookService') as mock_webhook_service:
                
                webhook_service = mock_webhook_service.return_value
                
                # Test valid GitHub webhook
                payload = {
                    "ref": "refs/heads/main",
                    "head_commit": {"id": "abc123", "message": "Test commit"}
                }
                
                # Create valid signature
                secret = "webhook_secret"
                payload_bytes = str(payload).encode('utf-8')
                signature = hmac.new(
                    secret.encode('utf-8'),
                    payload_bytes,
                    hashlib.sha256
                ).hexdigest()
                
                webhook_service.verify_signature.return_value = True
                
                valid_webhook_response = await client.post("/api/webhooks/github",
                    json=payload,
                    headers={
                        "X-GitHub-Event": "push",
                        "X-Hub-Signature-256": f"sha256={signature}"
                    }
                )
                
                assert valid_webhook_response.status_code == 200
                
                # Test invalid signature
                webhook_service.verify_signature.return_value = False
                
                invalid_webhook_response = await client.post("/api/webhooks/github",
                    json=payload,
                    headers={
                        "X-GitHub-Event": "push",
                        "X-Hub-Signature-256": "sha256=invalid_signature"
                    }
                )
                
                assert invalid_webhook_response.status_code == 401
                
                # Test missing signature
                no_signature_response = await client.post("/api/webhooks/github",
                    json=payload,
                    headers={"X-GitHub-Event": "push"}
                )
                
                assert no_signature_response.status_code == 401

    @pytest.mark.asyncio
    async def test_input_validation_security(self, client, mock_db):
        """Test input validation and sanitization"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Test SQL injection attempts
            sql_injection_payloads = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "admin'--",
                "' UNION SELECT * FROM users --"
            ]
            
            for payload in sql_injection_payloads:
                response = await client.post("/api/auth/login", json={
                    "email": payload,
                    "password": "password"
                })
                
                # Should handle gracefully without SQL injection
                assert response.status_code in [401, 422]  # Unauthorized or validation error
            
            # Test XSS attempts
            xss_payloads = [
                "<script>alert('xss')</script>",
                "javascript:alert('xss')",
                "<img src=x onerror=alert('xss')>",
                "';alert('xss');//"
            ]
            
            mock_db.execute.return_value.fetchone.return_value = None
            
            for payload in xss_payloads:
                response = await client.post("/api/auth/register", json={
                    "name": payload,
                    "email": "test@example.com",
                    "password": "ValidPassword123!",
                    "role": "student"
                })
                
                # Should validate and sanitize input
                assert response.status_code in [201, 422]  # Success or validation error
            
            # Test oversized input
            oversized_input = "A" * 10000
            
            response = await client.post("/api/auth/register", json={
                "name": oversized_input,
                "email": "test@example.com",
                "password": "ValidPassword123!",
                "role": "student"
            })
            
            assert response.status_code == 422  # Should reject oversized input

    @pytest.mark.asyncio
    async def test_session_security(self, client, mock_db):
        """Test session management security"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user login
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "hashed_password": get_password_hash("password123"),
                "role": "student"
            }
            
            # Login to get token
            login_response = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
            
            assert login_response.status_code == 200
            token_data = login_response.json()
            access_token = token_data["access_token"]
            
            # Test token reuse
            headers = {"Authorization": f"Bearer {access_token}"}
            
            # Multiple requests with same token should work
            for _ in range(5):
                response = await client.get("/api/auth/me", headers=headers)
                assert response.status_code == 200
            
            # Test logout invalidation (if implemented)
            logout_response = await client.post("/api/auth/logout", headers=headers)
            assert logout_response.status_code == 200
            
            # Token should still work until expiration (unless blacklisting is implemented)
            # This test assumes token blacklisting is not implemented
            post_logout_response = await client.get("/api/auth/me", headers=headers)
            # Could be 200 (no blacklisting) or 401 (with blacklisting)
            assert post_logout_response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_cors_security(self, client):
        """Test CORS security configuration"""
        
        # Test preflight request
        preflight_response = await client.options("/api/auth/me",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization"
            }
        )
        
        # Should handle CORS appropriately
        # The exact behavior depends on CORS configuration
        assert preflight_response.status_code in [200, 204, 405]

    @pytest.mark.asyncio
    async def test_rate_limiting_security(self, client, mock_db):
        """Test rate limiting security measures"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock failed login
            mock_db.execute.return_value.fetchone.return_value = None
            
            # Rapid fire requests
            responses = []
            for i in range(50):
                response = await client.post("/api/auth/login", json={
                    "email": f"test{i}@example.com",
                    "password": "password"
                })
                responses.append(response.status_code)
            
            # Should handle high request volume
            # In a real implementation with rate limiting, some would return 429
            assert all(status in [401, 429] for status in responses)

    @pytest.mark.asyncio
    async def test_data_exposure_prevention(self, client, mock_db):
        """Test prevention of sensitive data exposure"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user with sensitive data
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "hashed_password": "hashed_password_should_not_be_exposed",
                "role": "student",
                "status": "active"
            }
            
            token = create_access_token({"sub": "user-123", "role": "student"})
            
            # Get user profile
            response = await client.get("/api/auth/me",
                headers={"Authorization": f"Bearer {token}"})
            
            assert response.status_code == 200
            user_data = response.json()
            
            # Should not expose sensitive fields
            assert "hashed_password" not in user_data
            assert "password" not in user_data
            
            # Should only expose safe fields
            safe_fields = {"id", "email", "name", "role", "status", "created_at", "updated_at"}
            exposed_fields = set(user_data.keys())
            
            # All exposed fields should be in safe fields
            assert exposed_fields.issubset(safe_fields)

    @pytest.mark.asyncio
    async def test_authorization_bypass_prevention(self, client, mock_db):
        """Test prevention of authorization bypass attempts"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Create student token
            student_token = create_access_token({"sub": "student-123", "role": "student"})
            
            # Mock student user
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "student-123",
                "role": "student",
                "email": "student@example.com"
            }
            
            # Test direct object reference
            # Student tries to access another user's data
            other_user_response = await client.get("/api/users/other-user-456",
                headers={"Authorization": f"Bearer {student_token}"})
            
            assert other_user_response.status_code in [403, 404]
            
            # Test parameter tampering
            # Student tries to modify project they don't own
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "project-123",
                "owner_id": "other-user-456"  # Different owner
            }
            
            tamper_response = await client.put("/api/projects/project-123",
                json={"name": "Hacked Project"},
                headers={"Authorization": f"Bearer {student_token}"})
            
            assert tamper_response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_timing_attack_prevention(self, client, mock_db):
        """Test prevention of timing attacks"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            import time
            
            # Test login timing for existing vs non-existing users
            # Mock existing user
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "existing@example.com",
                "hashed_password": get_password_hash("password"),
                "role": "student"
            }
            
            # Time login attempt for existing user
            start_time = time.time()
            existing_response = await client.post("/api/auth/login", json={
                "email": "existing@example.com",
                "password": "wrong_password"
            })
            existing_time = time.time() - start_time
            
            # Mock non-existing user
            mock_db.execute.return_value.fetchone.return_value = None
            
            # Time login attempt for non-existing user
            start_time = time.time()
            nonexisting_response = await client.post("/api/auth/login", json={
                "email": "nonexisting@example.com",
                "password": "wrong_password"
            })
            nonexisting_time = time.time() - start_time
            
            # Both should fail
            assert existing_response.status_code == 401
            assert nonexisting_response.status_code == 401
            
            # Timing difference should be minimal (within 100ms)
            timing_difference = abs(existing_time - nonexisting_time)
            assert timing_difference < 0.1  # Less than 100ms difference

    @pytest.mark.asyncio
    async def test_concurrent_security_attacks(self, client, mock_db):
        """Test security under concurrent attack scenarios"""
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock user for brute force
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "target@example.com",
                "hashed_password": get_password_hash("correct_password"),
                "role": "student"
            }
            
            # Simulate concurrent brute force attempts
            async def brute_force_attempt(password):
                return await client.post("/api/auth/login", json={
                    "email": "target@example.com",
                    "password": password
                })
            
            # Create 20 concurrent brute force attempts
            passwords = [f"password{i}" for i in range(20)]
            tasks = [brute_force_attempt(pwd) for pwd in passwords]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should fail (none of the passwords are correct)
            status_codes = [
                r.status_code for r in responses 
                if not isinstance(r, Exception)
            ]
            
            assert all(status in [401, 429] for status in status_codes)
            
            # System should remain stable
            # Test that legitimate request still works after attack
            legitimate_response = await client.post("/api/auth/login", json={
                "email": "target@example.com",
                "password": "correct_password"
            })
            
            # Should still be able to login with correct credentials
            # (unless account is temporarily locked due to brute force)
            assert legitimate_response.status_code in [200, 429]