"""
Comprehensive database migration and rollback testing.
"""

import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, inspect
from alembic.config import Config
from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations
import tempfile
import os
from unittest.mock import patch

from app.core.database import Base
from app.models.user import User as UserModel
from app.models.project import Project as ProjectModel
from app.models.activity import Activity as ActivityModel
from app.models.repository import Repository as RepositoryModel
from app.models.deployment import Deployment as DeploymentModel


class TestDatabaseMigrations:
    """Comprehensive database migration testing"""

    @pytest.fixture(scope="class")
    def test_db_url(self):
        """Test database URL for migration testing"""
        return "postgresql+asyncpg://ticolops:password@localhost/ticolops_migration_test"

    @pytest.fixture(scope="class")
    async def migration_engine(self, test_db_url):
        """Create engine for migration testing"""
        engine = create_async_engine(test_db_url, echo=False)
        yield engine
        await engine.dispose()

    @pytest.fixture
    async def clean_database(self, migration_engine):
        """Ensure clean database state for each test"""
        async with migration_engine.begin() as conn:
            # Drop all tables
            await conn.run_sync(Base.metadata.drop_all)
            
            # Drop alembic version table if it exists
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            await conn.commit()

    @pytest.fixture
    def alembic_config(self):
        """Create Alembic configuration for testing"""
        # Create temporary alembic.ini for testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
            f.write("""
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://ticolops:password@localhost/ticolops_migration_test

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
""")
            config_path = f.name

        config = Config(config_path)
        yield config
        
        # Cleanup
        os.unlink(config_path)

    @pytest.mark.asyncio
    async def test_initial_migration(self, migration_engine, clean_database, alembic_config):
        """Test initial database migration creates all required tables"""
        
        # Run initial migration
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            command.upgrade(alembic_config, "head")
        
        # Verify all tables were created
        async with migration_engine.connect() as conn:
            inspector = inspect(conn.sync_engine)
            tables = inspector.get_table_names()
            
            expected_tables = [
                'users', 'projects', 'project_members', 'repositories', 
                'deployments', 'activities', 'notifications', 'webhooks',
                'alembic_version'
            ]
            
            for table in expected_tables:
                assert table in tables, f"Table {table} was not created"

    @pytest.mark.asyncio
    async def test_migration_rollback(self, migration_engine, clean_database, alembic_config):
        """Test migration rollback functionality"""
        
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            
            # Apply migrations
            command.upgrade(alembic_config, "head")
            
            # Verify tables exist
            async with migration_engine.connect() as conn:
                inspector = inspect(conn.sync_engine)
                tables_after_upgrade = inspector.get_table_names()
                assert len(tables_after_upgrade) > 1
            
            # Rollback to base
            command.downgrade(alembic_config, "base")
            
            # Verify tables are removed (except alembic_version)
            async with migration_engine.connect() as conn:
                inspector = inspect(conn.sync_engine)
                tables_after_downgrade = inspector.get_table_names()
                
                # Only alembic_version should remain
                assert len(tables_after_downgrade) <= 1
                if tables_after_downgrade:
                    assert tables_after_downgrade[0] == 'alembic_version'

    @pytest.mark.asyncio
    async def test_incremental_migrations(self, migration_engine, clean_database, alembic_config):
        """Test incremental migration steps"""
        
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            
            # Get all migration revisions
            from alembic.script import ScriptDirectory
            script_dir = ScriptDirectory.from_config(alembic_config)
            revisions = list(script_dir.walk_revisions())
            
            if len(revisions) > 1:
                # Apply migrations one by one
                for i, revision in enumerate(reversed(revisions)):
                    command.upgrade(alembic_config, revision.revision)
                    
                    # Verify database state at each step
                    async with migration_engine.connect() as conn:
                        inspector = inspect(conn.sync_engine)
                        tables = inspector.get_table_names()
                        
                        # Should have alembic_version at minimum
                        assert 'alembic_version' in tables
                        
                        # Check version is correct
                        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                        current_version = result.scalar()
                        assert current_version == revision.revision

    @pytest.mark.asyncio
    async def test_data_preservation_during_migration(self, migration_engine, clean_database, alembic_config):
        """Test that data is preserved during schema migrations"""
        
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            
            # Apply initial migration
            command.upgrade(alembic_config, "head")
            
            # Insert test data
            TestSessionLocal = async_sessionmaker(migration_engine, class_=AsyncSession)
            async with TestSessionLocal() as session:
                # Create test user
                test_user = UserModel(
                    id="test-user-123",
                    email="test@example.com",
                    name="Test User",
                    hashed_password="hashed_password",
                    role="student",
                    status="active"
                )
                session.add(test_user)
                await session.commit()
                
                # Verify data was inserted
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                count = result.scalar()
                assert count == 1
            
            # Simulate a migration that adds a column (if such migration exists)
            # For this test, we'll just verify the data survives a downgrade/upgrade cycle
            
            # Downgrade to previous version (if exists)
            from alembic.script import ScriptDirectory
            script_dir = ScriptDirectory.from_config(alembic_config)
            revisions = list(script_dir.walk_revisions())
            
            if len(revisions) > 1:
                previous_revision = revisions[1].revision
                command.downgrade(alembic_config, previous_revision)
                command.upgrade(alembic_config, "head")
                
                # Verify data still exists
                async with TestSessionLocal() as session:
                    result = await session.execute(text("SELECT email FROM users WHERE id = 'test-user-123'"))
                    email = result.scalar()
                    assert email == "test@example.com"

    @pytest.mark.asyncio
    async def test_foreign_key_constraints(self, migration_engine, clean_database, alembic_config):
        """Test that foreign key constraints are properly created"""
        
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            
            command.upgrade(alembic_config, "head")
            
            async with migration_engine.connect() as conn:
                inspector = inspect(conn.sync_engine)
                
                # Check foreign keys on project_members table
                if 'project_members' in inspector.get_table_names():
                    fks = inspector.get_foreign_keys('project_members')
                    fk_tables = [fk['referred_table'] for fk in fks]
                    
                    assert 'users' in fk_tables
                    assert 'projects' in fk_tables
                
                # Check foreign keys on activities table
                if 'activities' in inspector.get_table_names():
                    fks = inspector.get_foreign_keys('activities')
                    fk_tables = [fk['referred_table'] for fk in fks]
                    
                    assert 'users' in fk_tables
                    assert 'projects' in fk_tables

    @pytest.mark.asyncio
    async def test_index_creation(self, migration_engine, clean_database, alembic_config):
        """Test that database indexes are properly created"""
        
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            
            command.upgrade(alembic_config, "head")
            
            async with migration_engine.connect() as conn:
                inspector = inspect(conn.sync_engine)
                
                # Check indexes on users table
                if 'users' in inspector.get_table_names():
                    indexes = inspector.get_indexes('users')
                    index_columns = [idx['column_names'] for idx in indexes]
                    
                    # Should have index on email
                    assert any('email' in cols for cols in index_columns)
                
                # Check indexes on activities table
                if 'activities' in inspector.get_table_names():
                    indexes = inspector.get_indexes('activities')
                    index_columns = [idx['column_names'] for idx in indexes]
                    
                    # Should have indexes for performance
                    assert len(indexes) > 0

    @pytest.mark.asyncio
    async def test_migration_performance(self, migration_engine, clean_database, alembic_config):
        """Test migration performance with large datasets"""
        
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            
            import time
            
            # Measure migration time
            start_time = time.time()
            command.upgrade(alembic_config, "head")
            migration_time = time.time() - start_time
            
            # Migration should complete within reasonable time
            assert migration_time < 30.0  # 30 seconds max for initial migration
            
            # Insert large dataset
            TestSessionLocal = async_sessionmaker(migration_engine, class_=AsyncSession)
            async with TestSessionLocal() as session:
                # Insert 1000 test users
                users = []
                for i in range(1000):
                    user = UserModel(
                        id=f"user-{i}",
                        email=f"user{i}@example.com",
                        name=f"User {i}",
                        hashed_password="hashed_password",
                        role="student",
                        status="active"
                    )
                    users.append(user)
                
                session.add_all(users)
                await session.commit()
            
            # Test migration with data
            start_time = time.time()
            command.downgrade(alembic_config, "base")
            command.upgrade(alembic_config, "head")
            migration_with_data_time = time.time() - start_time
            
            # Should still complete within reasonable time
            assert migration_with_data_time < 60.0  # 1 minute max with data

    @pytest.mark.asyncio
    async def test_concurrent_migrations(self, migration_engine, clean_database, alembic_config):
        """Test behavior with concurrent migration attempts"""
        
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            
            async def run_migration():
                try:
                    command.upgrade(alembic_config, "head")
                    return True
                except Exception as e:
                    return str(e)
            
            # Try to run migrations concurrently
            tasks = [run_migration() for _ in range(3)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # At least one should succeed
            successful_migrations = [r for r in results if r is True]
            assert len(successful_migrations) >= 1
            
            # Verify final state is correct
            async with migration_engine.connect() as conn:
                inspector = inspect(conn.sync_engine)
                tables = inspector.get_table_names()
                assert len(tables) > 1  # Should have created tables

    @pytest.mark.asyncio
    async def test_migration_error_handling(self, migration_engine, clean_database, alembic_config):
        """Test migration error handling and recovery"""
        
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            
            # Apply successful migration first
            command.upgrade(alembic_config, "head")
            
            # Verify successful state
            async with migration_engine.connect() as conn:
                inspector = inspect(conn.sync_engine)
                tables_before = inspector.get_table_names()
                assert len(tables_before) > 1
            
            # Simulate migration failure by trying to apply same migration again
            try:
                # This should handle gracefully
                command.upgrade(alembic_config, "head")
            except Exception as e:
                # Should not break the database state
                pass
            
            # Verify database is still in good state
            async with migration_engine.connect() as conn:
                inspector = inspect(conn.sync_engine)
                tables_after = inspector.get_table_names()
                assert tables_after == tables_before

    @pytest.mark.asyncio
    async def test_schema_validation_after_migration(self, migration_engine, clean_database, alembic_config):
        """Test that schema matches SQLAlchemy models after migration"""
        
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            
            command.upgrade(alembic_config, "head")
            
            # Test that we can create model instances
            TestSessionLocal = async_sessionmaker(migration_engine, class_=AsyncSession)
            async with TestSessionLocal() as session:
                # Test User model
                user = UserModel(
                    id="schema-test-user",
                    email="schema@example.com",
                    name="Schema Test",
                    hashed_password="hashed",
                    role="student",
                    status="active"
                )
                session.add(user)
                
                # Test Project model
                project = ProjectModel(
                    id="schema-test-project",
                    name="Schema Test Project",
                    description="Test project",
                    owner_id="schema-test-user"
                )
                session.add(project)
                
                await session.commit()
                
                # Verify data was inserted correctly
                result = await session.execute(text("SELECT name FROM users WHERE id = 'schema-test-user'"))
                user_name = result.scalar()
                assert user_name == "Schema Test"
                
                result = await session.execute(text("SELECT name FROM projects WHERE id = 'schema-test-project'"))
                project_name = result.scalar()
                assert project_name == "Schema Test Project"

    @pytest.mark.asyncio
    async def test_migration_backup_and_restore(self, migration_engine, clean_database, alembic_config):
        """Test migration with backup and restore capabilities"""
        
        with patch('alembic.config.Config.get_main_option') as mock_get_option:
            mock_get_option.return_value = str(migration_engine.url)
            
            # Apply migration and add data
            command.upgrade(alembic_config, "head")
            
            TestSessionLocal = async_sessionmaker(migration_engine, class_=AsyncSession)
            async with TestSessionLocal() as session:
                user = UserModel(
                    id="backup-test-user",
                    email="backup@example.com",
                    name="Backup Test",
                    hashed_password="hashed",
                    role="student",
                    status="active"
                )
                session.add(user)
                await session.commit()
            
            # Create a "backup" by storing current data
            async with migration_engine.connect() as conn:
                result = await conn.execute(text("SELECT COUNT(*) FROM users"))
                user_count_before = result.scalar()
            
            # Simulate rollback and restore
            command.downgrade(alembic_config, "base")
            command.upgrade(alembic_config, "head")
            
            # In a real scenario, we would restore data from backup
            # For this test, we verify the schema is ready for data restoration
            async with TestSessionLocal() as session:
                # Verify we can insert the same data again
                user = UserModel(
                    id="backup-test-user-restored",
                    email="restored@example.com",
                    name="Restored User",
                    hashed_password="hashed",
                    role="student",
                    status="active"
                )
                session.add(user)
                await session.commit()
                
                result = await session.execute(text("SELECT name FROM users WHERE id = 'backup-test-user-restored'"))
                restored_name = result.scalar()
                assert restored_name == "Restored User"