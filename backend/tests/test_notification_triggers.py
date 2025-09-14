"""Tests for notification triggers system."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification_triggers import NotificationTriggerService
from app.models.user import User
from app.models.project import Project
from app.models.deployment import Deployment, DeploymentStatus
from app.models.activity import Activity, ActivityType
from app.models.notification import NotificationPriority, NotificationCategory


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=AsyncSession)


@pytest.fixture
def mock_notification_service():
    """Mock notification service."""
    service = Mock()
    service.create_notification = AsyncMock()
    return service


@pytest.fixture
def trigger_service(mock_db, mock_notification_service):
    """Create notification trigger service with mocked dependencies."""
    service = NotificationTriggerService(mock_db)
    service.notification_service = mock_notification_service
    return service


@pytest.fixture
def sample_user():
    """Sample user for testing."""
    return User(
        id="user-123",
        email="test@example.com",
        name="Test User",
        username="testuser",
        role="student",
        status="online",
        last_activity=datetime.utcnow()
    )


@pytest.fixture
def sample_project():
    """Sample project for testing."""
    return Project(
        id="project-123",
        name="Test Project",
        description="A test project",
        owner_id="user-123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_deployment():
    """Sample deployment for testing."""
    return type('Deployment', (), {
        'id': 'deployment-123',
        'repository_id': 'repo-123',
        'branch': 'main',
        'commit_hash': 'abc123def456',
        'environment': 'production',
        'status': DeploymentStatus.SUCCESS,
        'url': 'https://test-app.vercel.app',
        'logs': ['Build started', 'Build completed'],
        'started_at': datetime.utcnow() - timedelta(minutes=5),
        'completed_at': datetime.utcnow()
    })()


@pytest.fixture
def sample_activity():
    """Sample activity for testing."""
    return Activity(
        id="activity-123",
        user_id="user-123",
        project_id="project-123",
        type=ActivityType.CODING,
        location="src/components/TestComponent.tsx",
        timestamp=datetime.utcnow(),
        metadata={}
    )


class TestNotificationTriggerService:
    """Test cases for NotificationTriggerService."""
    
    @pytest.mark.asyncio
    async def test_handle_deployment_success(
        self,
        trigger_service,
        sample_deployment,
        mock_notification_service
    ):
        """Test handling successful deployment notifications."""
        # Mock repository and project data
        with patch.object(trigger_service, '_get_repository') as mock_get_repo, \
             patch.object(trigger_service, '_get_project') as mock_get_project, \
             patch.object(trigger_service, '_get_project_members') as mock_get_members:
            
            mock_repo = type('Repository', (), {
                'id': 'repo-123',
                'name': 'test-repo',
                'project_id': 'project-123'
            })()
            
            mock_project = type('Project', (), {
                'id': 'project-123',
                'name': 'Test Project'
            })()
            
            mock_members = [
                type('Member', (), {'user_id': 'user-1'}),
                type('Member', (), {'user_id': 'user-2'})
            ]
            
            mock_get_repo.return_value = mock_repo
            mock_get_project.return_value = mock_project
            mock_get_members.return_value = mock_members
            
            # Execute the test
            await trigger_service.handle_deployment_event(
                sample_deployment,
                "deployment_success",
                {}
            )
            
            # Verify notifications were created
            assert mock_notification_service.create_notification.call_count == 2
            
            # Check notification data
            call_args = mock_notification_service.create_notification.call_args_list[0]
            kwargs = call_args[1]
            
            assert kwargs['type'] == 'deployment_success'
            assert kwargs['title'] == '✅ Deployment Successful - test-repo'
            assert kwargs['priority'] == NotificationPriority.HIGH
            assert kwargs['category'] == NotificationCategory.DEPLOYMENT
    
    @pytest.mark.asyncio
    async def test_handle_deployment_failure(
        self,
        trigger_service,
        sample_deployment,
        mock_notification_service
    ):
        """Test handling failed deployment notifications."""
        # Set deployment to failed status
        sample_deployment.status = DeploymentStatus.FAILED
        
        error_data = {
            "error": "Build failed: Missing dependency"
        }
        
        with patch.object(trigger_service, '_get_repository') as mock_get_repo, \
             patch.object(trigger_service, '_get_project') as mock_get_project, \
             patch.object(trigger_service, '_get_interested_users') as mock_get_users:
            
            mock_repo = type('Repository', (), {
                'id': 'repo-123',
                'name': 'test-repo',
                'project_id': 'project-123'
            })()
            
            mock_project = type('Project', (), {
                'id': 'project-123',
                'name': 'Test Project'
            })()
            
            mock_users = [
                type('User', (), {'id': 'user-1'}),
                type('User', (), {'id': 'user-2'})
            ]
            
            mock_get_repo.return_value = mock_repo
            mock_get_project.return_value = mock_project
            mock_get_users.return_value = mock_users
            
            # Execute the test
            await trigger_service.handle_deployment_event(
                sample_deployment,
                "deployment_failed",
                error_data
            )
            
            # Verify notifications were created
            assert mock_notification_service.create_notification.call_count == 2
            
            # Check notification data
            call_args = mock_notification_service.create_notification.call_args_list[0]
            kwargs = call_args[1]
            
            assert kwargs['type'] == 'deployment_failed'
            assert kwargs['title'] == '❌ Deployment Failed - test-repo'
            assert kwargs['priority'] == NotificationPriority.HIGH
            assert 'Build failed' in kwargs['message']
    
    @pytest.mark.asyncio
    async def test_detect_mentions(
        self,
        trigger_service,
        sample_user,
        sample_project,
        mock_notification_service
    ):
        """Test mention detection and notification."""
        content = "Hey @testuser, can you review this code? Also @anotheruser should see this."
        context = {
            "type": "comment",
            "id": "comment-123",
            "url": "/projects/project-123/comments/123"
        }
        
        with patch.object(trigger_service, '_get_project_members') as mock_get_members:
            # Mock project members
            mock_members = [
                type('Member', (), {
                    'user': type('User', (), {
                        'id': 'user-1',
                        'username': 'testuser',
                        'name': 'Test User'
                    })()
                }),
                type('Member', (), {
                    'user': type('User', (), {
                        'id': 'user-2',
                        'username': 'anotheruser',
                        'name': 'Another User'
                    })()
                })
            ]
            
            mock_get_members.return_value = mock_members
            
            # Execute the test
            mentions = await trigger_service.detect_and_handle_mentions(
                content,
                sample_user,
                sample_project,
                context
            )
            
            # Verify mentions were detected
            assert len(mentions) == 2
            assert 'testuser' in mentions
            assert 'anotheruser' in mentions
            
            # Verify notifications were created (excluding self-mention)
            assert mock_notification_service.create_notification.call_count == 1
    
    @pytest.mark.asyncio
    async def test_handle_activity_conflict(
        self,
        trigger_service,
        sample_activity,
        sample_user,
        sample_project,
        mock_notification_service
    ):
        """Test handling activity conflict notifications."""
        conflict_data = {
            "conflicting_users": ["user-123", "user-456"],
            "severity": "high"
        }
        
        with patch.object(trigger_service, '_get_project') as mock_get_project, \
             patch.object(trigger_service, '_get_user') as mock_get_user, \
             patch.object(trigger_service, '_get_project_members') as mock_get_members:
            
            mock_get_project.return_value = sample_project
            mock_get_user.return_value = sample_user
            mock_get_members.return_value = []
            
            # Execute the test
            await trigger_service.handle_activity_event(
                sample_activity,
                "conflict_detected",
                conflict_data
            )
            
            # Verify notifications were created for conflicting users
            assert mock_notification_service.create_notification.call_count == 2
            
            # Check notification data
            call_args = mock_notification_service.create_notification.call_args_list[0]
            kwargs = call_args[1]
            
            assert kwargs['type'] == 'conflict_detected'
            assert kwargs['title'] == '⚠️ Potential Conflict Detected'
            assert kwargs['priority'] == NotificationPriority.HIGH
            assert kwargs['category'] == NotificationCategory.COLLABORATION
    
    @pytest.mark.asyncio
    async def test_handle_collaboration_help_request(
        self,
        trigger_service,
        sample_user,
        sample_project,
        mock_notification_service
    ):
        """Test handling help request notifications."""
        help_data = {
            "component": "authentication module",
            "description": "Having trouble with JWT token validation",
            "urgency": "high"
        }
        
        with patch.object(trigger_service, '_get_project') as mock_get_project, \
             patch.object(trigger_service, '_get_user') as mock_get_user, \
             patch.object(trigger_service, '_get_project_members') as mock_get_members:
            
            mock_members = [
                type('Member', (), {'user_id': 'user-123'}),  # Requester
                type('Member', (), {'user_id': 'user-456'}),  # Helper 1
                type('Member', (), {'user_id': 'user-789'})   # Helper 2
            ]
            
            mock_get_project.return_value = sample_project
            mock_get_user.return_value = sample_user
            mock_get_members.return_value = mock_members
            
            # Execute the test
            await trigger_service.handle_collaboration_trigger(
                "help_requested",
                sample_project.id,
                sample_user.id,
                help_data
            )
            
            # Verify notifications were created for other team members (not requester)
            assert mock_notification_service.create_notification.call_count == 2
            
            # Check notification data
            call_args = mock_notification_service.create_notification.call_args_list[0]
            kwargs = call_args[1]
            
            assert kwargs['type'] == 'help_requested'
            assert kwargs['title'] == '🆘 Help Requested'
            assert kwargs['priority'] == NotificationPriority.HIGH
            assert 'authentication module' in kwargs['message']
    
    @pytest.mark.asyncio
    async def test_handle_work_completion(
        self,
        trigger_service,
        sample_user,
        sample_project,
        mock_notification_service
    ):
        """Test handling work completion notifications."""
        completion_data = {
            "component": "user registration",
            "type": "feature"
        }
        
        with patch.object(trigger_service, '_get_project') as mock_get_project, \
             patch.object(trigger_service, '_get_user') as mock_get_user, \
             patch.object(trigger_service, '_get_project_members') as mock_get_members, \
             patch.object(trigger_service, '_get_members_interested_in_location') as mock_get_interested:
            
            mock_interested_members = [
                type('Member', (), {'user_id': 'user-456'}),
                type('Member', (), {'user_id': 'user-789'})
            ]
            
            mock_get_project.return_value = sample_project
            mock_get_user.return_value = sample_user
            mock_get_members.return_value = []
            mock_get_interested.return_value = mock_interested_members
            
            # Execute the test
            await trigger_service.handle_collaboration_trigger(
                "work_completed",
                sample_project.id,
                sample_user.id,
                completion_data
            )
            
            # Verify notifications were created for interested members
            assert mock_notification_service.create_notification.call_count == 2
            
            # Check notification data
            call_args = mock_notification_service.create_notification.call_args_list[0]
            kwargs = call_args[1]
            
            assert kwargs['type'] == 'work_completed'
            assert kwargs['title'] == '✅ Work Completed'
            assert kwargs['priority'] == NotificationPriority.MEDIUM
            assert 'user registration' in kwargs['message']
    
    def test_mention_pattern_detection(self, trigger_service):
        """Test mention pattern regex."""
        test_cases = [
            ("Hello @username", ["username"]),
            ("@user1 and @user2 are working", ["user1", "user2"]),
            ("Email test@example.com is not a mention", []),
            ("@user_name and @user-name work", ["user_name", "user-name"]),
            ("No mentions here", []),
            ("@123user starts with number", ["123user"]),
        ]
        
        for content, expected in test_cases:
            matches = trigger_service.mention_pattern.findall(content)
            assert matches == expected, f"Failed for content: {content}"
    
    @pytest.mark.asyncio
    async def test_error_handling_in_deployment_event(
        self,
        trigger_service,
        sample_deployment
    ):
        """Test error handling in deployment event processing."""
        with patch.object(trigger_service, '_get_repository') as mock_get_repo:
            # Simulate repository not found
            mock_get_repo.return_value = None
            
            # Should not raise exception, just log warning
            await trigger_service.handle_deployment_event(
                sample_deployment,
                "deployment_success",
                {}
            )
            
            # Verify repository was checked
            mock_get_repo.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_error_handling_in_activity_event(
        self,
        trigger_service,
        sample_activity
    ):
        """Test error handling in activity event processing."""
        with patch.object(trigger_service, '_get_project') as mock_get_project:
            # Simulate project not found
            mock_get_project.return_value = None
            
            # Should not raise exception, just log warning
            await trigger_service.handle_activity_event(
                sample_activity,
                "activity_started",
                {}
            )
            
            # Verify project was checked
            mock_get_project.assert_called_once()


class TestMentionDetection:
    """Test cases specifically for mention detection functionality."""
    
    @pytest.mark.asyncio
    async def test_mention_detection_case_insensitive(
        self,
        trigger_service,
        sample_user,
        sample_project,
        mock_notification_service
    ):
        """Test that mention detection is case insensitive."""
        content = "Hey @TestUser, check this out!"
        
        with patch.object(trigger_service, '_get_project_members') as mock_get_members:
            mock_members = [
                type('Member', (), {
                    'user': type('User', (), {
                        'id': 'user-1',
                        'username': 'testuser',  # lowercase in database
                        'name': 'Test User'
                    })()
                })
            ]
            
            mock_get_members.return_value = mock_members
            
            mentions = await trigger_service.detect_and_handle_mentions(
                content,
                sample_user,
                sample_project,
                {}
            )
            
            # Should detect the mention despite case difference
            assert len(mentions) == 1
            assert mentions[0] == 'TestUser'
    
    @pytest.mark.asyncio
    async def test_mention_detection_excludes_self(
        self,
        trigger_service,
        sample_user,
        sample_project,
        mock_notification_service
    ):
        """Test that users don't get notified for mentioning themselves."""
        content = "I'm working on @testuser's code"
        
        with patch.object(trigger_service, '_get_project_members') as mock_get_members:
            mock_members = [
                type('Member', (), {
                    'user': type('User', (), {
                        'id': sample_user.id,
                        'username': sample_user.username,
                        'name': sample_user.name
                    })()
                })
            ]
            
            mock_get_members.return_value = mock_members
            
            mentions = await trigger_service.detect_and_handle_mentions(
                content,
                sample_user,
                sample_project,
                {}
            )
            
            # Should detect the mention but not create notification
            assert len(mentions) == 0  # Self-mentions are filtered out
            assert mock_notification_service.create_notification.call_count == 0
    
    @pytest.mark.asyncio
    async def test_mention_detection_invalid_users(
        self,
        trigger_service,
        sample_user,
        sample_project,
        mock_notification_service
    ):
        """Test mention detection with users not in project."""
        content = "Hey @nonexistentuser, check this!"
        
        with patch.object(trigger_service, '_get_project_members') as mock_get_members:
            mock_members = []  # No members
            mock_get_members.return_value = mock_members
            
            mentions = await trigger_service.detect_and_handle_mentions(
                content,
                sample_user,
                sample_project,
                {}
            )
            
            # Should not detect invalid mentions
            assert len(mentions) == 0
            assert mock_notification_service.create_notification.call_count == 0


if __name__ == "__main__":
    pytest.main([__file__])