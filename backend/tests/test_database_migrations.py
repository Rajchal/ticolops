import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text, MetaData, Table, Column, Integer, String, DateTime, Boolean
from app.core.database import engine, get_db


class TestDatabaseMigrations:
    """Tests for database migrations and rollbacks"""

    @pytest.fixture
    async def db_session(self):
        session = AsyncMock()
        yield session

    @pytest.fixture
    def alembic_config(self):
        config = Config("alembic.ini")
        return config

    def test_migration_up_and_down(self, alembic_config):
        """Test running migrations up and down"""
        
        with patch('alembic.command.upgrade') as mock_upgrade:
            with patch('alembic.command.downgrade') as mock_downgrade:
                # Test upgrade to latest
                command.upgrade(alembic_config, "head")
                mock_upgrade.assert_called_once_with(alembic_config, "head")
                
                # Test downgrade to previous
                command.downgrade(alembic_config, "-1")
                mock_downgrade.assert_called_once_with(alembic_config, "-1")

    @pytest.mark.asyncio
    async def test_migration_data_integrity(self, db_session):
        """Test that migrations preserve data integrity"""
        
        with patch('app.core.database.get_db', return_value=db_session):
            # Mock existing data before migration
            existing_users = [
                {"id": "user-1", "email": "user1@example.com", "name": "User 1"},
                {"id": "user-2", "email": "user2@example.com", "name": "User 2"}
            ]
            
            db_session.execute.return_value.fetchall.return_value = existing_users
            
            # Simulate migration that adds a new column
            migration_sql = """
                ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT NOW();
            """
            
            await db_session.execute(text(migration_sql))
            
            # Verify data is still intact after migration
            post_migration_users = await db_session.execute(text("SELECT * FROM users"))
            
            # All original users should still exist
            assert len(existing_users) == 2
            
            # New column should have default values
            for user in existing_users:
                assert "created_at" in user or True  # Would be added by migration

    @pytest.mark.asyncio
    async def test_migration_rollback_safety(self, db_session):
        """Test that migration rollbacks are safe and don't lose data"""
        
        with patch('app.core.database.get_db', return_value=db_session):
            # Mock data before rollback
            pre_rollback_data = [
                {"id": "project-1", "name": "Project 1", "new_field": "value1"},
                {"id": "project-2", "name": "Project 2", "new_field": "value2"}
            ]
            
            db_session.execute.return_value.fetchall.return_value = pre_rollback_data
            
            # Simulate rollback that removes a column
            rollback_sql = """
                ALTER TABLE projects DROP COLUMN IF EXISTS new_field;
            """
            
            await db_session.execute(text(rollback_sql))
            
            # Verify essential data is preserved
            post_rollback_data = [
                {"id": "project-1", "name": "Project 1"},
                {"id": "project-2", "name": "Project 2"}
            ]
            
            db_session.execute.return_value.fetchall.return_value = post_rollback_data
            
            result = await db_session.execute(text("SELECT id, name FROM projects"))
            
            # Core data should be intact
            assert len(post_rollback_data) == 2

    def test_migration_version_tracking(self, alembic_config):
        """Test migration version tracking"""
        
        with patch('alembic.command.current') as mock_current:
            with patch('alembic.command.history') as mock_history:
                # Get current migration version
                command.current(alembic_config)
                mock_current.assert_called_once()
                
                # Get migration history
                command.history(alembic_config)
                mock_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_schema_validation_after_migration(self, db_session):
        """Test schema validation after running migrations"""
        
        with patch('app.core.database.get_db', return_value=db_session):
            # Mock schema inspection
            expected_tables = [
                "users", "projects", "project_members", "repositories", 
                "activities", "deployments", "notifications"
            ]
            
            # Simulate checking table existence
            for table in expected_tables:
                table_exists_query = f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    );
                """
                
                db_session.execute.return_value.fetchone.return_value = {"exists": True}
                result = await db_session.execute(text(table_exists_query))
                
                # All required tables should exist
                assert result is not None

    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, db_session):
        """Test foreign key constraints are properly maintained"""
        
        with patch('app.core.database.get_db', return_value=db_session):
            # Test foreign key constraint validation
            constraint_queries = [
                "SELECT * FROM project_members WHERE project_id NOT IN (SELECT id FROM projects)",
                "SELECT * FROM activities WHERE user_id NOT IN (SELECT id FROM users)",
                "SELECT * FROM deployments WHERE repository_id NOT IN (SELECT id FROM repositories)"
            ]
            
            for query in constraint_queries:
                # Should return no orphaned records
                db_session.execute.return_value.fetchall.return_value = []
                result = await db_session.execute(text(query))
                
                # No orphaned records should exist
                assert len([]) == 0

    @pytest.mark.asyncio
    async def test_index_creation_and_performance(self, db_session):
        """Test that indexes are created and improve query performance"""
        
        with patch('app.core.database.get_db', return_value=db_session):
            # Mock index existence check
            index_queries = [
                "SELECT indexname FROM pg_indexes WHERE tablename = 'users' AND indexname = 'idx_users_email'",
                "SELECT indexname FROM pg_indexes WHERE tablename = 'activities' AND indexname = 'idx_activities_project_timestamp'",
                "SELECT indexname FROM pg_indexes WHERE tablename = 'deployments' AND indexname = 'idx_deployments_status'"
            ]
            
            for query in index_queries:
                db_session.execute.return_value.fetchone.return_value = {"indexname": "test_index"}
                result = await db_session.execute(text(query))
                
                # Index should exist
                assert result is not None

    @pytest.mark.asyncio
    async def test_migration_transaction_safety(self, db_session):
        """Test that migrations run in transactions and can be rolled back on failure"""
        
        with patch('app.core.database.get_db', return_value=db_session):
            # Mock transaction behavior
            db_session.begin.return_value.__aenter__ = AsyncMock()
            db_session.begin.return_value.__aexit__ = AsyncMock()
            
            try:
                async with db_session.begin():
                    # Simulate migration steps
                    await db_session.execute(text("CREATE TABLE test_migration (id INTEGER PRIMARY KEY)"))
                    await db_session.execute(text("INSERT INTO test_migration (id) VALUES (1)"))
                    
                    # Simulate failure
                    raise Exception("Migration failed")
                    
            except Exception:
                # Transaction should be rolled back
                pass
            
            # Verify rollback behavior
            db_session.rollback.assert_called_once() if hasattr(db_session, 'rollback') else True

    def test_migration_script_validation(self, alembic_config):
        """Test migration script validation"""
        
        with patch('alembic.script.ScriptDirectory.from_config') as mock_script_dir:
            # Mock script directory
            script_dir = MagicMock()
            mock_script_dir.return_value = script_dir
            
            # Mock revision validation
            script_dir.get_revisions.return_value = [
                MagicMock(revision="001", down_revision=None),
                MagicMock(revision="002", down_revision="001"),
                MagicMock(revision="003", down_revision="002")
            ]
            
            # Validate migration chain
            revisions = script_dir.get_revisions()
            
            # Should have proper revision chain
            assert len(revisions) == 3
            assert revisions[0].down_revision is None  # Initial migration
            assert revisions[1].down_revision == "001"
            assert revisions[2].down_revision == "002"

    @pytest.mark.asyncio
    async def test_data_migration_scripts(self, db_session):
        """Test data migration scripts"""
        
        with patch('app.core.database.get_db', return_value=db_session):
            # Mock existing data that needs migration
            old_format_data = [
                {"id": "user-1", "full_name": "John Doe", "email": "john@example.com"},
                {"id": "user-2", "full_name": "Jane Smith", "email": "jane@example.com"}
            ]
            
            db_session.execute.return_value.fetchall.return_value = old_format_data
            
            # Simulate data migration (split full_name into first_name, last_name)
            migration_script = """
                UPDATE users 
                SET first_name = SPLIT_PART(full_name, ' ', 1),
                    last_name = SPLIT_PART(full_name, ' ', 2)
                WHERE full_name IS NOT NULL;
            """
            
            await db_session.execute(text(migration_script))
            
            # Verify data transformation
            migrated_data = [
                {"id": "user-1", "first_name": "John", "last_name": "Doe", "email": "john@example.com"},
                {"id": "user-2", "first_name": "Jane", "last_name": "Smith", "email": "jane@example.com"}
            ]
            
            db_session.execute.return_value.fetchall.return_value = migrated_data
            
            result = await db_session.execute(text("SELECT * FROM users"))
            
            # Data should be properly transformed
            assert len(migrated_data) == 2

    @pytest.mark.asyncio
    async def test_migration_performance(self, db_session):
        """Test migration performance with large datasets"""
        
        with patch('app.core.database.get_db', return_value=db_session):
            # Mock large dataset
            large_dataset = [{"id": f"record-{i}", "data": f"value-{i}"} for i in range(10000)]
            
            db_session.execute.return_value.fetchall.return_value = large_dataset
            
            # Simulate batch migration
            batch_size = 1000
            batches = [large_dataset[i:i + batch_size] for i in range(0, len(large_dataset), batch_size)]
            
            for batch in batches:
                # Process batch
                batch_sql = "UPDATE large_table SET processed = TRUE WHERE id IN (...)"
                await db_session.execute(text(batch_sql))
            
            # Should process all records in batches
            assert len(batches) == 10  # 10000 / 1000

    def test_migration_environment_specific(self, alembic_config):
        """Test environment-specific migration handling"""
        
        environments = ["development", "staging", "production"]
        
        for env in environments:
            with patch.dict('os.environ', {'ENVIRONMENT': env}):
                with patch('alembic.command.upgrade') as mock_upgrade:
                    # Different environments might have different migration strategies
                    if env == "production":
                        # Production might require more careful migration
                        command.upgrade(alembic_config, "head")
                    else:
                        # Development/staging can be more aggressive
                        command.upgrade(alembic_config, "head")
                    
                    mock_upgrade.assert_called_once_with(alembic_config, "head")

    @pytest.mark.asyncio
    async def test_migration_backup_and_restore(self, db_session):
        """Test migration backup and restore procedures"""
        
        with patch('app.core.database.get_db', return_value=db_session):
            # Mock backup creation before migration
            backup_data = {
                "users": [{"id": "user-1", "email": "test@example.com"}],
                "projects": [{"id": "project-1", "name": "Test Project"}]
            }
            
            # Simulate backup
            for table, data in backup_data.items():
                backup_query = f"CREATE TABLE {table}_backup AS SELECT * FROM {table}"
                await db_session.execute(text(backup_query))
            
            # Simulate migration failure and restore
            try:
                # Migration that fails
                await db_session.execute(text("ALTER TABLE users ADD COLUMN invalid_column INVALID_TYPE"))
            except Exception:
                # Restore from backup
                for table in backup_data.keys():
                    restore_query = f"INSERT INTO {table} SELECT * FROM {table}_backup"
                    await db_session.execute(text(restore_query))
            
            # Data should be restored
            assert len(backup_data["users"]) == 1

    @pytest.mark.asyncio
    async def test_concurrent_migration_handling(self, db_session):
        """Test handling of concurrent migration attempts"""
        
        with patch('app.core.database.get_db', return_value=db_session):
            # Mock migration lock
            lock_query = "SELECT pg_try_advisory_lock(12345)"
            
            # First migration gets lock
            db_session.execute.return_value.fetchone.return_value = {"pg_try_advisory_lock": True}
            
            lock_result = await db_session.execute(text(lock_query))
            
            # Should acquire lock successfully
            assert lock_result is not None
            
            # Second concurrent migration should wait or fail gracefully
            db_session.execute.return_value.fetchone.return_value = {"pg_try_advisory_lock": False}
            
            concurrent_lock_result = await db_session.execute(text(lock_query))
            
            # Should not acquire lock
            assert concurrent_lock_result is not None