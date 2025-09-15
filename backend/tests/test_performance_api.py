import pytest
import asyncio
import time
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from app.main import app
from app.core.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.activity import Activity


class TestAPIPerformance:
    """Performance tests for API endpoints"""

    @pytest.fixture
    async def client(self):
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    def test_auth_login_performance(self, benchmark, client, mock_db):
        """Test login endpoint performance"""
        
        async def login_request():
            response = await client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
            return response
        
        # Mock database operations
        with patch('app.core.database.get_db', return_value=mock_db):
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "user-123",
                "email": "test@example.com",
                "hashed_password": "$2b$12$hash",
                "name": "Test User",
                "role": "student"
            }
            
            # Benchmark the login request
            result = benchmark(asyncio.run, login_request())
            
        # Should complete within 100ms
        assert benchmark.stats.mean < 0.1

    def test_project_list_performance(self, benchmark, client, mock_db):
        """Test project listing performance with large dataset"""
        
        # Create mock data for 1000 projects
        mock_projects = [
            {
                "id": f"project-{i}",
                "name": f"Project {i}",
                "description": f"Description for project {i}",
                "owner_id": "user-123",
                "created_at": "2024-01-01T00:00:00Z"
            }
            for i in range(1000)
        ]
        
        async def get_projects():
            response = await client.get("/api/projects", headers={
                "Authorization": "Bearer test-token"
            })
            return response
        
        with patch('app.core.database.get_db', return_value=mock_db):
            mock_db.execute.return_value.fetchall.return_value = mock_projects
            
            result = benchmark(asyncio.run, get_projects())
            
        # Should handle 1000 projects within 200ms
        assert benchmark.stats.mean < 0.2

    def test_activity_feed_performance(self, benchmark, client, mock_db):
        """Test activity feed performance with high volume"""
        
        # Create mock activity data
        mock_activities = [
            {
                "id": f"activity-{i}",
                "user_id": f"user-{i % 10}",
                "project_id": "project-123",
                "type": "coding",
                "location": f"src/component-{i}.tsx",
                "timestamp": "2024-01-01T00:00:00Z",
                "metadata": {"action": "edit"}
            }
            for i in range(500)
        ]
        
        async def get_activity_feed():
            response = await client.get("/api/projects/project-123/activities", headers={
                "Authorization": "Bearer test-token"
            })
            return response
        
        with patch('app.core.database.get_db', return_value=mock_db):
            mock_db.execute.return_value.fetchall.return_value = mock_activities
            
            result = benchmark(asyncio.run, get_activity_feed())
            
        # Should handle 500 activities within 150ms
        assert benchmark.stats.mean < 0.15

    def test_websocket_message_throughput(self, benchmark):
        """Test WebSocket message processing throughput"""
        
        from app.websocket.connection_manager import ConnectionManager
        
        manager = ConnectionManager()
        
        def process_messages():
            # Simulate processing 100 messages
            messages = [
                {
                    "type": "activity_update",
                    "payload": {
                        "user_id": f"user-{i % 10}",
                        "location": f"file-{i}.py",
                        "action": "edit"
                    }
                }
                for i in range(100)
            ]
            
            start_time = time.time()
            for message in messages:
                # Simulate message processing
                manager._process_message(message)
            
            return time.time() - start_time
        
        # Benchmark message processing
        processing_time = benchmark(process_messages)
        
        # Should process 100 messages within 50ms
        assert processing_time < 0.05

    def test_concurrent_api_requests(self, benchmark, client, mock_db):
        """Test API performance under concurrent load"""
        
        async def concurrent_requests():
            # Simulate 50 concurrent requests
            tasks = []
            
            for i in range(50):
                task = client.get(f"/api/projects/project-{i % 5}/activities", headers={
                    "Authorization": "Bearer test-token"
                })
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            return responses
        
        with patch('app.core.database.get_db', return_value=mock_db):
            mock_db.execute.return_value.fetchall.return_value = []
            
            result = benchmark(asyncio.run, concurrent_requests())
            
        # Should handle 50 concurrent requests within 500ms
        assert benchmark.stats.mean < 0.5

    def test_database_query_performance(self, benchmark, mock_db):
        """Test database query performance"""
        
        from app.services.project_service import ProjectService
        
        service = ProjectService()
        
        async def complex_query():
            # Simulate complex query with joins
            query_result = await service.get_project_with_members_and_activities("project-123")
            return query_result
        
        with patch('app.core.database.get_db', return_value=mock_db):
            # Mock complex query result
            mock_db.execute.return_value.fetchone.return_value = {
                "id": "project-123",
                "name": "Test Project",
                "members": [{"id": "user-1"}, {"id": "user-2"}],
                "activities": [{"id": "activity-1"}, {"id": "activity-2"}]
            }
            
            result = benchmark(asyncio.run, complex_query())
            
        # Complex queries should complete within 100ms
        assert benchmark.stats.mean < 0.1

    def test_deployment_pipeline_performance(self, benchmark, client, mock_db):
        """Test deployment pipeline API performance"""
        
        async def trigger_deployment():
            response = await client.post("/api/projects/project-123/deployments", 
                json={
                    "branch": "main",
                    "environment": "staging"
                },
                headers={"Authorization": "Bearer test-token"}
            )
            return response
        
        with patch('app.core.database.get_db', return_value=mock_db):
            with patch('app.services.deployment_service.DeploymentService.trigger_deployment') as mock_deploy:
                mock_deploy.return_value = {
                    "id": "deploy-123",
                    "status": "pending",
                    "branch": "main"
                }
                
                result = benchmark(asyncio.run, trigger_deployment())
                
        # Deployment trigger should be fast (under 200ms)
        assert benchmark.stats.mean < 0.2

    def test_notification_broadcast_performance(self, benchmark):
        """Test notification broadcasting performance"""
        
        from app.services.notification_service import NotificationService
        
        service = NotificationService()
        
        def broadcast_notifications():
            # Simulate broadcasting to 100 users
            notification = {
                "title": "Deployment Complete",
                "message": "Your deployment to staging is ready",
                "type": "success"
            }
            
            user_ids = [f"user-{i}" for i in range(100)]
            
            start_time = time.time()
            for user_id in user_ids:
                service._send_notification(user_id, notification)
            
            return time.time() - start_time
        
        # Benchmark notification broadcasting
        broadcast_time = benchmark(broadcast_notifications)
        
        # Should broadcast to 100 users within 100ms
        assert broadcast_time < 0.1

    def test_memory_usage_under_load(self, benchmark, client, mock_db):
        """Test memory usage during high load"""
        
        import psutil
        import os
        
        async def memory_intensive_operations():
            # Perform multiple memory-intensive operations
            tasks = []
            
            for i in range(20):
                # Create large mock datasets
                large_dataset = [{"id": j, "data": "x" * 1000} for j in range(1000)]
                
                task = client.post("/api/projects/project-123/bulk-activities",
                    json={"activities": large_dataset[:100]},  # Send subset
                    headers={"Authorization": "Bearer test-token"}
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            return responses
        
        # Measure memory before
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        with patch('app.core.database.get_db', return_value=mock_db):
            mock_db.execute.return_value = None
            
            result = benchmark(asyncio.run, memory_intensive_operations())
        
        # Measure memory after
        memory_after = process.memory_info().rss
        memory_increase = memory_after - memory_before
        
        # Memory increase should be reasonable (under 100MB)
        assert memory_increase < 100 * 1024 * 1024

    def test_cache_performance(self, benchmark):
        """Test caching system performance"""
        
        from app.core.cache import CacheService
        
        cache = CacheService()
        
        def cache_operations():
            # Test cache set/get performance
            start_time = time.time()
            
            # Set 1000 cache entries
            for i in range(1000):
                cache.set(f"key-{i}", {"data": f"value-{i}"}, ttl=300)
            
            # Get 1000 cache entries
            for i in range(1000):
                cache.get(f"key-{i}")
            
            return time.time() - start_time
        
        # Benchmark cache operations
        cache_time = benchmark(cache_operations)
        
        # 2000 cache operations should complete within 100ms
        assert cache_time < 0.1