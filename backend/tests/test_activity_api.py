"""Tests for activity tracking API endpoints."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from app.schemas.activity import ActivityType, ActivityPriority, UserPresenceStatus
from app.models.activity import Activity, UserPresence
from app.models.user import User


class TestActivityAPI:
    """Test cases for activity API endpoints."""

    @pytest.mark.asyncio
    async def test_create_activity_success(self, client, mock_current_user, mock_db_session):
        """Test successful activity creation."""
        # Mock activity service
        with patch('app.api.activity.ActivityService') as mock_service:
            mock_activity = Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Test activity",
                user_id=mock_current_user.id,
                priority=ActivityPriority.MEDIUM.value,
                metadata={}
            )
            mock_service.return_value.create_activity.return_value = mock_activity
            
            # Request data
            activity_data = {
                "type": "coding",
                "title": "Test activity",
                "description": "Testing activity creation",
                "location": "src/test.py",
                "priority": "medium"
            }
            
            # Make request
            response = await client.post("/activities", json=activity_data)
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["type"] == "coding"
            assert data["title"] == "Test activity"
            assert data["user_id"] == str(mock_current_user.id)

    @pytest.mark.asyncio
    async def test_create_activity_invalid_data(self, client, mock_current_user):
        """Test activity creation with invalid data."""
        # Invalid activity data (missing required fields)
        activity_data = {
            "description": "Missing required fields"
        }
        
        # Make request
        response = await client.post("/activities", json=activity_data)
        
        # Verify validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_activities_success(self, client, mock_current_user, mock_db_session):
        """Test successful activities retrieval."""
        # Mock activity service
        with patch('app.api.activity.ActivityService') as mock_service:
            mock_activities = [
                Activity(
                    id=uuid4(),
                    type=ActivityType.CODING.value,
                    title="Activity 1",
                    user_id=mock_current_user.id,
                    priority=ActivityPriority.HIGH.value,
                    metadata={},
                    created_at=datetime.utcnow()
                ),
                Activity(
                    id=uuid4(),
                    type=ActivityType.TESTING.value,
                    title="Activity 2",
                    user_id=mock_current_user.id,
                    priority=ActivityPriority.MEDIUM.value,
                    metadata={},
                    created_at=datetime.utcnow()
                )
            ]
            mock_service.return_value.get_activities.return_value = mock_activities
            
            # Make request with filters
            response = await client.get(
                "/activities",
                params={
                    "user_id": str(mock_current_user.id),
                    "activity_types": "coding,testing",
                    "limit": 10
                }
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["type"] == "coding"
            assert data[1]["type"] == "testing"

    @pytest.mark.asyncio
    async def test_get_activities_invalid_date_format(self, client, mock_current_user):
        """Test activities retrieval with invalid date format."""
        # Make request with invalid date
        response = await client.get(
            "/activities",
            params={"start_date": "invalid-date-format"}
        )
        
        # Verify bad request error
        assert response.status_code == 400
        assert "Invalid parameter" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_update_activity_success(self, client, mock_current_user, mock_db_session):
        """Test successful activity update."""
        activity_id = str(uuid4())
        
        # Mock activity service
        with patch('app.api.activity.ActivityService') as mock_service:
            mock_activity = Activity(
                id=uuid4(activity_id),
                type=ActivityType.CODING.value,
                title="Updated activity",
                user_id=mock_current_user.id,
                priority=ActivityPriority.HIGH.value,
                metadata={}
            )
            mock_service.return_value.update_activity.return_value = mock_activity
            
            # Update data
            update_data = {
                "title": "Updated activity",
                "priority": "high",
                "description": "Updated description"
            }
            
            # Make request
            response = await client.put(f"/activities/{activity_id}", json=update_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "Updated activity"
            assert data["priority"] == "high"

    @pytest.mark.asyncio
    async def test_update_activity_not_found(self, client, mock_current_user, mock_db_session):
        """Test activity update with non-existent activity."""
        activity_id = str(uuid4())
        
        # Mock activity service to raise NotFoundError
        with patch('app.api.activity.ActivityService') as mock_service:
            from app.core.exceptions import NotFoundError
            mock_service.return_value.update_activity.side_effect = NotFoundError("Activity not found")
            
            # Update data
            update_data = {"title": "Updated activity"}
            
            # Make request
            response = await client.put(f"/activities/{activity_id}", json=update_data)
            
            # Verify not found error
            assert response.status_code == 404
            assert "Activity not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_end_activity_success(self, client, mock_current_user, mock_db_session):
        """Test successfully ending an activity."""
        activity_id = str(uuid4())
        
        # Mock activity service
        with patch('app.api.activity.ActivityService') as mock_service:
            mock_activity = Activity(
                id=uuid4(activity_id),
                type=ActivityType.CODING.value,
                title="Ended activity",
                user_id=mock_current_user.id,
                priority=ActivityPriority.MEDIUM.value,
                metadata={},
                ended_at=datetime.utcnow(),
                duration_seconds="1800"  # 30 minutes
            )
            mock_service.return_value.end_activity.return_value = mock_activity
            
            # Make request
            response = await client.post(f"/activities/{activity_id}/end")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["ended_at"] is not None
            assert data["duration_seconds"] == "1800"

    @pytest.mark.asyncio
    async def test_create_batch_activities_success(self, client, mock_current_user, mock_db_session):
        """Test successful batch activity creation."""
        # Mock activity service
        with patch('app.api.activity.ActivityService') as mock_service:
            mock_activities = [
                Activity(
                    id=uuid4(),
                    type=ActivityType.CODING.value,
                    title="Batch activity 1",
                    user_id=mock_current_user.id,
                    priority=ActivityPriority.MEDIUM.value,
                    metadata={}
                ),
                Activity(
                    id=uuid4(),
                    type=ActivityType.TESTING.value,
                    title="Batch activity 2",
                    user_id=mock_current_user.id,
                    priority=ActivityPriority.LOW.value,
                    metadata={}
                )
            ]
            mock_service.return_value.create_batch_activities.return_value = mock_activities
            
            # Batch data
            batch_data = {
                "activities": [
                    {
                        "type": "coding",
                        "title": "Batch activity 1",
                        "priority": "medium"
                    },
                    {
                        "type": "testing",
                        "title": "Batch activity 2",
                        "priority": "low"
                    }
                ]
            }
            
            # Make request
            response = await client.post("/activities/batch", json=batch_data)
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert len(data) == 2
            assert data[0]["type"] == "coding"
            assert data[1]["type"] == "testing"

    @pytest.mark.asyncio
    async def test_get_activity_stats_success(self, client, mock_current_user, mock_db_session):
        """Test successful activity statistics retrieval."""
        # Mock activity service
        with patch('app.api.activity.ActivityService') as mock_service:
            from app.schemas.activity import ActivityStats
            mock_stats = ActivityStats(
                total_activities=10,
                activities_by_type={"coding": 6, "testing": 4},
                activities_by_priority={"high": 3, "medium": 5, "low": 2},
                most_active_locations=[
                    {"location": "src/main.py", "count": 5},
                    {"location": "tests/test_main.py", "count": 3}
                ],
                activity_timeline=[
                    {"date": "2024-01-15", "count": 5},
                    {"date": "2024-01-16", "count": 5}
                ],
                collaboration_metrics={
                    "unique_locations": 8,
                    "average_activities_per_day": 5.0,
                    "most_active_day": "2024-01-15"
                }
            )
            mock_service.return_value.get_activity_stats.return_value = mock_stats
            
            # Make request
            response = await client.get(
                "/activities/stats",
                params={"days": 7}
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["total_activities"] == 10
            assert data["activities_by_type"]["coding"] == 6
            assert len(data["most_active_locations"]) == 2

    @pytest.mark.asyncio
    async def test_get_activity_stats_access_denied(self, client, mock_current_user, mock_db_session):
        """Test activity stats access denied for other users."""
        other_user_id = str(uuid4())
        
        # Make request for another user's stats (non-admin)
        response = await client.get(
            "/activities/stats",
            params={"user_id": other_user_id}
        )
        
        # Verify access denied
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]


class TestPresenceAPI:
    """Test cases for presence API endpoints."""

    @pytest.mark.asyncio
    async def test_update_presence_success(self, client, mock_current_user, mock_db_session):
        """Test successful presence update."""
        # Mock presence service
        with patch('app.api.activity.PresenceService') as mock_service:
            mock_presence = UserPresence(
                id=uuid4(),
                user_id=mock_current_user.id,
                status=UserPresenceStatus.ONLINE.value,
                current_location="src/main.py",
                current_activity=ActivityType.CODING.value,
                last_seen=datetime.utcnow(),
                session_started=datetime.utcnow(),
                last_activity=datetime.utcnow(),
                metadata={}
            )
            mock_service.return_value.update_presence.return_value = mock_presence
            
            # Presence data
            presence_data = {
                "status": "online",
                "current_location": "src/main.py",
                "current_activity": "coding",
                "metadata": {"browser": "chrome"}
            }
            
            # Make request
            response = await client.post("/presence", json=presence_data)
            
            # Verify response
            assert response.status_code == 201
            data = response.json()
            assert data["status"] == "online"
            assert data["current_location"] == "src/main.py"
            assert data["current_activity"] == "coding"

    @pytest.mark.asyncio
    async def test_get_project_presence_success(self, client, mock_current_user, mock_db_session):
        """Test successful project presence retrieval."""
        project_id = str(uuid4())
        
        # Mock presence service
        with patch('app.api.activity.PresenceService') as mock_service:
            mock_presence_list = [
                UserPresence(
                    id=uuid4(),
                    user_id=uuid4(),
                    project_id=uuid4(project_id),
                    status=UserPresenceStatus.ONLINE.value,
                    current_location="src/file1.py",
                    last_activity=datetime.utcnow(),
                    metadata={}
                ),
                UserPresence(
                    id=uuid4(),
                    user_id=uuid4(),
                    project_id=uuid4(project_id),
                    status=UserPresenceStatus.ACTIVE.value,
                    current_location="src/file2.py",
                    last_activity=datetime.utcnow(),
                    metadata={}
                )
            ]
            mock_service.return_value.get_project_presence.return_value = mock_presence_list
            
            # Make request
            response = await client.get(f"/presence/project/{project_id}")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["status"] == "online"
            assert data[1]["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_online_users_success(self, client, mock_current_user, mock_db_session):
        """Test successful online users retrieval."""
        # Mock presence service
        with patch('app.api.activity.PresenceService') as mock_service:
            mock_online_users = [
                UserPresence(
                    id=uuid4(),
                    user_id=uuid4(),
                    status=UserPresenceStatus.ONLINE.value,
                    last_activity=datetime.utcnow(),
                    metadata={}
                ),
                UserPresence(
                    id=uuid4(),
                    user_id=uuid4(),
                    status=UserPresenceStatus.ACTIVE.value,
                    last_activity=datetime.utcnow(),
                    metadata={}
                )
            ]
            mock_service.return_value.get_online_users.return_value = mock_online_users
            
            # Make request
            response = await client.get("/presence/online")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert all(user["status"] in ["online", "active"] for user in data)

    @pytest.mark.asyncio
    async def test_get_collaboration_opportunities_success(self, client, mock_current_user, mock_db_session):
        """Test successful collaboration opportunities retrieval."""
        project_id = str(uuid4())
        
        # Mock presence service
        with patch('app.api.activity.PresenceService') as mock_service:
            from app.schemas.activity import CollaborationOpportunity
            mock_opportunities = [
                CollaborationOpportunity(
                    type="same_file",
                    users=[str(mock_current_user.id), str(uuid4())],
                    location="src/shared.py",
                    description="Both users working on same file",
                    priority=ActivityPriority.HIGH,
                    metadata={"file_type": "python"}
                ),
                CollaborationOpportunity(
                    type="related_files",
                    users=[str(mock_current_user.id), str(uuid4())],
                    location="src/auth/",
                    description="Working on related authentication files",
                    priority=ActivityPriority.MEDIUM,
                    metadata={"module": "auth"}
                )
            ]
            mock_service.return_value.detect_collaboration_opportunities.return_value = mock_opportunities
            
            # Make request
            response = await client.get(f"/collaboration/opportunities/{project_id}")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["type"] == "same_file"
            assert data[1]["type"] == "related_files"

    @pytest.mark.asyncio
    async def test_get_project_conflicts_success(self, client, mock_current_user, mock_db_session):
        """Test successful project conflicts retrieval."""
        project_id = str(uuid4())
        
        # Mock presence service
        with patch('app.api.activity.PresenceService') as mock_service:
            from app.schemas.activity import ConflictDetection
            mock_conflicts = [
                ConflictDetection(
                    type="concurrent_editing",
                    users=[str(uuid4()), str(uuid4())],
                    location="src/critical.py",
                    description="Multiple users editing same file",
                    severity="high",
                    suggested_resolution="Coordinate changes via chat",
                    metadata={"conflict_duration": "15 minutes"}
                )
            ]
            mock_service.return_value.detect_conflicts.return_value = mock_conflicts
            
            # Make request
            response = await client.get(f"/collaboration/conflicts/{project_id}")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["type"] == "concurrent_editing"
            assert data[0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_cleanup_stale_presence_success(self, client, mock_admin_user, mock_db_session):
        """Test successful stale presence cleanup (admin only)."""
        # Mock presence service
        with patch('app.api.activity.PresenceService') as mock_service:
            mock_service.return_value.cleanup_stale_presence.return_value = 5
            
            # Make request as admin
            with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
                response = await client.post(
                    "/presence/cleanup",
                    params={"hours": 48}
                )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["cleaned_count"] == 5
            assert data["hours_threshold"] == 48

    @pytest.mark.asyncio
    async def test_cleanup_stale_presence_access_denied(self, client, mock_current_user, mock_db_session):
        """Test stale presence cleanup access denied for non-admin."""
        # Make request as non-admin user
        response = await client.post("/presence/cleanup")
        
        # Verify access denied
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_activity_system_health_check_success(self, client, mock_db_session):
        """Test successful activity system health check."""
        # Mock database queries
        mock_db_session.execute.return_value.scalar.side_effect = [25, 5]  # 25 activities, 5 online users
        
        # Make request
        response = await client.get("/health/activity-system")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["metrics"]["recent_activities_24h"] == 25
        assert data["metrics"]["currently_online_users"] == 5
        assert data["features"]["activity_tracking"] == "operational"

    @pytest.mark.asyncio
    async def test_activity_system_health_check_degraded(self, client, mock_db_session):
        """Test activity system health check with database error."""
        # Mock database error
        mock_db_session.execute.side_effect = Exception("Database connection failed")
        
        # Make request
        response = await client.get("/health/activity-system")
        
        # Verify degraded response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert "Database connection failed" in data["error"]


@pytest.fixture
def mock_admin_user():
    """Mock admin user for testing."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        name="Admin User",
        hashed_password="hashed_password",
        role="admin",
        status="active"
    )