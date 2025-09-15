import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch
from sqlalchemy import text
from app.core.database import get_db, engine
from app.models.user import User
from app.models.project import Project
from app.models.activity import Activity


class TestDatabasePerformance:
    """Performance tests for database operations"""

    @pytest.fixture
    async def db_session(self):
        # Mock database session for testing
        session = AsyncMock()
        yield session

    def test_user_query_performance(self, benchmark, db_session):
        """Test user-related query performance"""
        
        async def user_queries():
            # Simulate multiple user queries
            queries = [
                "SELECT * FROM users WHERE email = 'test@example.com'",
                "SELECT * FROM users WHERE id = 'user-123'",
                "SELECT u.*, p.name as project_name FROM users u JOIN project_members pm ON u.id = pm.user_id JOIN projects p ON pm.project_id = p.id WHERE u.id = 'user-123'",
                "UPDATE users SET last_activity = NOW() WHERE id = 'user-123'",
                "SELECT COUNT(*) FROM users WHERE created_at > NOW() - INTERVAL '24 hours'"
            ]
            
            for query in queries:
                result = await db_session.execute(text(query))
            
            return len(queries)
        
        # Mock database responses
        db_session.execute.return_value.fetchone.return_value = {"id": "user-123"}
        db_session.execute.return_value.fetchall.return_value = [{"id": "user-123"}]
        
        result = benchmark(asyncio.run, user_queries())
        
        # 5 user queries should complete within 50ms
        assert benchmark.stats.mean < 0.05

    def test_project_query_performance(self, benchmark, db_session):
        """Test project-related query performance"""
        
        async def project_queries():
            # Complex project queries with joins
            queries = [
                """
                SELECT p.*, u.name as owner_name, 
                       COUNT(DISTINCT pm.user_id) as member_count,
                       COUNT(DISTINCT a.id) as activity_count
                FROM projects p
                LEFT JOIN users u ON p.owner_id = u.id
                LEFT JOIN project_members pm ON p.id = pm.project_id
                LEFT JOIN activities a ON p.id = a.project_id
                WHERE p.id = 'project-123'
                GROUP BY p.id, u.name
                """,
                """
                SELECT a.*, u.name as user_name
                FROM activities a
                JOIN users u ON a.user_id = u.id
                WHERE a.project_id = 'project-123'
                ORDER BY a.timestamp DESC
                LIMIT 50
                """,
                """
                SELECT pm.*, u.name, u.email, u.role
                FROM project_members pm
                JOIN users u ON pm.user_id = u.id
                WHERE pm.project_id = 'project-123'
                """,
                """
                INSERT INTO activities (id, user_id, project_id, type, location, timestamp, metadata)
                VALUES ('activity-123', 'user-123', 'project-123', 'coding', 'src/main.py', NOW(), '{}')
                """,
                """
                UPDATE projects SET updated_at = NOW() WHERE id = 'project-123'
                """
            ]
            
            for query in queries:
                result = await db_session.execute(text(query))
            
            return len(queries)
        
        # Mock responses
        db_session.execute.return_value.fetchone.return_value = {
            "id": "project-123",
            "member_count": 5,
            "activity_count": 100
        }
        db_session.execute.return_value.fetchall.return_value = [
            {"id": "activity-1", "user_name": "User 1"},
            {"id": "activity-2", "user_name": "User 2"}
        ]
        
        result = benchmark(asyncio.run, project_queries())
        
        # Complex project queries should complete within 100ms
        assert benchmark.stats.mean < 0.1

    def test_activity_bulk_insert_performance(self, benchmark, db_session):
        """Test bulk activity insertion performance"""
        
        async def bulk_insert_activities():
            # Simulate inserting 1000 activities
            activities = []
            for i in range(1000):
                activities.append({
                    "id": f"activity-{i}",
                    "user_id": f"user-{i % 10}",
                    "project_id": "project-123",
                    "type": "coding",
                    "location": f"src/file-{i}.py",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "metadata": "{}"
                })
            
            # Bulk insert using VALUES clause
            values_clause = ",".join([
                f"('{a['id']}', '{a['user_id']}', '{a['project_id']}', '{a['type']}', '{a['location']}', '{a['timestamp']}', '{a['metadata']}')"
                for a in activities
            ])
            
            query = f"""
                INSERT INTO activities (id, user_id, project_id, type, location, timestamp, metadata)
                VALUES {values_clause}
            """
            
            result = await db_session.execute(text(query))
            return len(activities)
        
        db_session.execute.return_value = AsyncMock()
        
        result = benchmark(asyncio.run, bulk_insert_activities())
        
        # Bulk insert of 1000 activities should complete within 200ms
        assert benchmark.stats.mean < 0.2

    def test_deployment_query_performance(self, benchmark, db_session):
        """Test deployment-related query performance"""
        
        async def deployment_queries():
            queries = [
                """
                SELECT d.*, r.name as repo_name, r.url as repo_url, u.name as triggered_by_name
                FROM deployments d
                JOIN repositories r ON d.repository_id = r.id
                JOIN users u ON d.triggered_by = u.id
                WHERE d.project_id = 'project-123'
                ORDER BY d.created_at DESC
                LIMIT 20
                """,
                """
                SELECT status, COUNT(*) as count
                FROM deployments
                WHERE project_id = 'project-123'
                AND created_at > NOW() - INTERVAL '30 days'
                GROUP BY status
                """,
                """
                SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration
                FROM deployments
                WHERE project_id = 'project-123'
                AND status = 'success'
                AND completed_at IS NOT NULL
                """,
                """
                UPDATE deployments 
                SET status = 'success', completed_at = NOW(), url = 'https://staging.example.com'
                WHERE id = 'deployment-123'
                """,
                """
                INSERT INTO deployment_logs (deployment_id, level, message, timestamp)
                VALUES ('deployment-123', 'info', 'Build completed successfully', NOW())
                """
            ]
            
            for query in queries:
                result = await db_session.execute(text(query))
            
            return len(queries)
        
        # Mock responses
        db_session.execute.return_value.fetchall.return_value = [
            {"id": "deploy-1", "status": "success"},
            {"id": "deploy-2", "status": "failed"}
        ]
        db_session.execute.return_value.fetchone.return_value = {"avg_duration": 120.5}
        
        result = benchmark(asyncio.run, deployment_queries())
        
        # Deployment queries should complete within 75ms
        assert benchmark.stats.mean < 0.075

    def test_notification_query_performance(self, benchmark, db_session):
        """Test notification-related query performance"""
        
        async def notification_queries():
            queries = [
                """
                SELECT n.*, u.name as user_name
                FROM notifications n
                JOIN users u ON n.user_id = u.id
                WHERE n.user_id = 'user-123'
                AND n.read_at IS NULL
                ORDER BY n.created_at DESC
                LIMIT 50
                """,
                """
                INSERT INTO notifications (id, user_id, title, message, type, created_at)
                VALUES ('notif-123', 'user-123', 'Deployment Complete', 'Your deployment is ready', 'success', NOW())
                """,
                """
                UPDATE notifications 
                SET read_at = NOW()
                WHERE user_id = 'user-123' AND id IN ('notif-1', 'notif-2', 'notif-3')
                """,
                """
                DELETE FROM notifications
                WHERE user_id = 'user-123'
                AND created_at < NOW() - INTERVAL '30 days'
                """,
                """
                SELECT type, COUNT(*) as count
                FROM notifications
                WHERE user_id = 'user-123'
                AND created_at > NOW() - INTERVAL '7 days'
                GROUP BY type
                """
            ]
            
            for query in queries:
                result = await db_session.execute(text(query))
            
            return len(queries)
        
        # Mock responses
        db_session.execute.return_value.fetchall.return_value = [
            {"id": "notif-1", "title": "Test Notification"}
        ]
        
        result = benchmark(asyncio.run, notification_queries())
        
        # Notification queries should complete within 60ms
        assert benchmark.stats.mean < 0.06

    def test_concurrent_database_operations(self, benchmark, db_session):
        """Test database performance under concurrent load"""
        
        async def concurrent_operations():
            # Simulate 50 concurrent database operations
            tasks = []
            
            for i in range(50):
                if i % 5 == 0:
                    # Read operations
                    task = db_session.execute(text(f"SELECT * FROM users WHERE id = 'user-{i}'"))
                elif i % 5 == 1:
                    # Write operations
                    task = db_session.execute(text(f"INSERT INTO activities (id, user_id, project_id, type) VALUES ('act-{i}', 'user-{i}', 'proj-1', 'coding')"))
                elif i % 5 == 2:
                    # Update operations
                    task = db_session.execute(text(f"UPDATE users SET last_activity = NOW() WHERE id = 'user-{i}'"))
                elif i % 5 == 3:
                    # Complex joins
                    task = db_session.execute(text(f"SELECT u.*, p.name FROM users u JOIN project_members pm ON u.id = pm.user_id JOIN projects p ON pm.project_id = p.id WHERE u.id = 'user-{i}'"))
                else:
                    # Aggregations
                    task = db_session.execute(text(f"SELECT COUNT(*) FROM activities WHERE user_id = 'user-{i}'"))
                
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return len(results)
        
        # Mock all operations
        db_session.execute.return_value.fetchone.return_value = {"id": "user-1"}
        db_session.execute.return_value.fetchall.return_value = [{"id": "user-1"}]
        
        result = benchmark(asyncio.run, concurrent_operations())
        
        # 50 concurrent operations should complete within 300ms
        assert benchmark.stats.mean < 0.3

    def test_index_performance(self, benchmark, db_session):
        """Test query performance with proper indexing"""
        
        async def indexed_queries():
            # Queries that should benefit from indexes
            queries = [
                "SELECT * FROM users WHERE email = 'test@example.com'",  # Index on email
                "SELECT * FROM activities WHERE project_id = 'project-123' ORDER BY timestamp DESC",  # Index on project_id, timestamp
                "SELECT * FROM deployments WHERE repository_id = 'repo-123' AND status = 'success'",  # Composite index
                "SELECT * FROM notifications WHERE user_id = 'user-123' AND read_at IS NULL",  # Index on user_id, read_at
                "SELECT * FROM project_members WHERE project_id = 'project-123' AND role = 'admin'"  # Composite index
            ]
            
            for query in queries:
                result = await db_session.execute(text(query))
            
            return len(queries)
        
        # Mock responses
        db_session.execute.return_value.fetchall.return_value = [{"id": "result-1"}]
        
        result = benchmark(asyncio.run, indexed_queries())
        
        # Indexed queries should be very fast (under 30ms)
        assert benchmark.stats.mean < 0.03

    def test_connection_pool_performance(self, benchmark):
        """Test database connection pool performance"""
        
        async def connection_pool_test():
            # Simulate getting and releasing connections rapidly
            connections = []
            
            # Get 20 connections
            for i in range(20):
                conn = await engine.connect()
                connections.append(conn)
            
            # Use connections
            for conn in connections:
                await conn.execute(text("SELECT 1"))
            
            # Release connections
            for conn in connections:
                await conn.close()
            
            return len(connections)
        
        with patch('app.core.database.engine') as mock_engine:
            mock_conn = AsyncMock()
            mock_conn.execute.return_value = AsyncMock()
            mock_engine.connect.return_value = mock_conn
            
            result = benchmark(asyncio.run, connection_pool_test())
        
        # Connection pool operations should be fast (under 100ms)
        assert benchmark.stats.mean < 0.1

    def test_transaction_performance(self, benchmark, db_session):
        """Test transaction performance"""
        
        async def transaction_operations():
            # Simulate complex transaction
            async with db_session.begin():
                # Multiple operations in single transaction
                await db_session.execute(text("INSERT INTO projects (id, name, owner_id) VALUES ('proj-123', 'Test Project', 'user-123')"))
                await db_session.execute(text("INSERT INTO project_members (project_id, user_id, role) VALUES ('proj-123', 'user-123', 'owner')"))
                await db_session.execute(text("INSERT INTO repositories (id, project_id, name, url) VALUES ('repo-123', 'proj-123', 'test-repo', 'https://github.com/test/repo')"))
                await db_session.execute(text("INSERT INTO activities (id, user_id, project_id, type) VALUES ('act-123', 'user-123', 'proj-123', 'project_created')"))
                await db_session.execute(text("UPDATE users SET project_count = project_count + 1 WHERE id = 'user-123'"))
            
            return 5  # Number of operations
        
        # Mock transaction context
        db_session.begin.return_value.__aenter__ = AsyncMock()
        db_session.begin.return_value.__aexit__ = AsyncMock()
        db_session.execute.return_value = AsyncMock()
        
        result = benchmark(asyncio.run, transaction_operations())
        
        # Transaction with 5 operations should complete within 80ms
        assert benchmark.stats.mean < 0.08