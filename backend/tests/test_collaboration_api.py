"""Tests for collaboration API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.schemas.activity import ConflictDetection, CollaborationOpportunity, ActivityPriority
from app.models.user import User


class TestCollaborationAPI:
    """Test cases for collaboration API endpoints."""

    @pytest.mark.asyncio
    async def test_get_project_conflicts_success(self, client, mock_current_user):
        """Test getting project conflicts successfully."""
        project_id = str(uuid4())
        
        with patch('app.api.collaboration.detect_project_conflicts') as mock_detect:
            mock_conflicts = [
                ConflictDetection(
                    type="concurrent_editing",
                    users=["user1", "user2"],
                    location="src/main.py",
                    description="Two users editing same file",
                    severity="medium"
                )
            ]
            mock_detect.return_value = mock_conflicts
            
            response = await client.get(f"/projects/{project_id}/conflicts")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["type"] == "concurrent_editing"
            assert data[0]["location"] == "src/main.py"
            
            # Verify detect was called
            mock_detect.assert_called_once_with(project_id)

    @pytest.mark.asyncio
    async def test_get_collaboration_opportunities_success(self, client, mock_current_user):
        """Test getting collaboration opportunities successfully."""
        project_id = str(uuid4())
        
        with patch('app.api.collaboration.find_collaboration_opportunities') as mock_find:
            mock_opportunities = [
                CollaborationOpportunity(
                    type="same_file",
                    users=[str(mock_current_user.id), "user2"],
                    location="src/main.py",
                    description="Both users working on same file",
                    priority=ActivityPriority.HIGH,
                    metadata={"opportunity_type": "real_time"}
                )
            ]
            mock_find.return_value = mock_opportunities
            
            response = await client.get(f"/projects/{project_id}/collaboration-opportunities")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["type"] == "same_file"
            assert data[0]["location"] == "src/main.py"
            assert data[0]["priority"] == "high"
            
            # Verify find was called with current user
            mock_find.assert_called_once_with(project_id, str(mock_current_user.id))

    @pytest.mark.asyncio
    async def test_get_collaboration_opportunities_specific_user(self, client, mock_current_user):
        """Test getting collaboration opportunities for specific user."""
        project_id = str(uuid4())
        target_user_id = str(mock_current_user.id)  # Same as current user
        
        with patch('app.api.collaboration.find_collaboration_opportunities') as mock_find:
            mock_find.return_value = []
            
            response = await client.get(
                f"/projects/{project_id}/collaboration-opportunities",
                params={"user_id": target_user_id}
            )
            
            # Verify response
            assert response.status_code == 200
            
            # Verify find was called with specified user
            mock_find.assert_called_once_with(project_id, target_user_id)

    @pytest.mark.asyncio
    async def test_get_collaboration_opportunities_access_denied(self, client, mock_current_user):
        """Test access denied when requesting other user's opportunities."""
        project_id = str(uuid4())
        other_user_id = str(uuid4())
        
        response = await client.get(
            f"/projects/{project_id}/collaboration-opportunities",
            params={"user_id": other_user_id}
        )
        
        # Verify access denied
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_analyze_conflict_success(self, client, mock_current_user):
        """Test analyzing conflict successfully."""
        conflict_id = str(uuid4())
        
        with patch('app.api.collaboration.conflict_detector') as mock_detector:
            mock_analysis = {
                "severity_score": 8,
                "urgency": "high",
                "impact_factors": ["Multiple users involved"],
                "recommended_actions": ["Coordinate immediately"]
            }
            mock_detector.analyze_conflict_severity = AsyncMock(return_value=mock_analysis)
            
            conflict_data = {
                "type": "concurrent_editing",
                "users": ["user1", "user2"],
                "location": "src/main.py",
                "description": "Conflict description",
                "severity": "high"
            }
            
            response = await client.post(f"/conflicts/{conflict_id}/analyze", json=conflict_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["conflict_id"] == conflict_id
            assert data["analysis"] == mock_analysis
            assert data["analyzed_by"] == str(mock_current_user.id)

    @pytest.mark.asyncio
    async def test_get_conflict_resolution_suggestions_success(self, client, mock_current_user):
        """Test getting conflict resolution suggestions."""
        conflict_id = str(uuid4())
        
        with patch('app.api.collaboration.conflict_detector') as mock_detector:
            mock_suggestions = {
                "primary_strategy": "Real-time coordination",
                "alternative_strategies": ["File locking", "Sequential editing"],
                "tools_recommended": ["Live Share", "Git merge tools"],
                "communication_channels": ["instant_message", "voice_call"],
                "timeline": "Immediate (within 15 minutes)"
            }
            mock_detector.suggest_conflict_resolution = AsyncMock(return_value=mock_suggestions)
            
            conflict_data = {
                "type": "concurrent_editing",
                "users": ["user1", "user2"],
                "location": "src/main.py",
                "description": "Conflict description",
                "severity": "medium"
            }
            
            response = await client.post(f"/conflicts/{conflict_id}/resolve", json=conflict_data)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["conflict_id"] == conflict_id
            assert data["resolution_suggestions"] == mock_suggestions
            assert data["suggested_by"] == str(mock_current_user.id)

    @pytest.mark.asyncio
    async def test_get_conflict_history_success(self, client, mock_current_user):
        """Test getting conflict history."""
        project_id = str(uuid4())
        
        with patch('app.api.collaboration.conflict_detector') as mock_detector:
            mock_history = {
                "total_conflicts": 5,
                "conflicts_by_type": {"concurrent_editing": 3, "overlapping_work": 2},
                "conflicts_by_severity": {"high": 2, "medium": 3},
                "frequent_conflict_locations": [
                    {"location": "src/main.py", "count": 3}
                ]
            }
            mock_detector.get_conflict_history = AsyncMock(return_value=mock_history)
            
            response = await client.get(f"/projects/{project_id}/conflict-history")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["project_id"] == project_id
            assert data["analysis_period_days"] == 7  # default
            assert data["history"] == mock_history

    @pytest.mark.asyncio
    async def test_get_conflict_history_custom_days(self, client, mock_current_user):
        """Test getting conflict history with custom days."""
        project_id = str(uuid4())
        
        with patch('app.api.collaboration.conflict_detector') as mock_detector:
            mock_detector.get_conflict_history = AsyncMock(return_value={})
            
            response = await client.get(
                f"/projects/{project_id}/conflict-history",
                params={"days": 14}
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["analysis_period_days"] == 14
            
            # Verify correct days were passed
            mock_detector.get_conflict_history.assert_called_once_with(project_id, 14)

    @pytest.mark.asyncio
    async def test_create_collaboration_session_success(self, client, mock_current_user):
        """Test creating collaboration session."""
        project_id = str(uuid4())
        
        session_data = {
            "participants": [str(mock_current_user.id), "user2"],
            "type": "pair_programming",
            "focus_area": "src/main.py",
            "duration_minutes": 90,
            "metadata": {"tools": ["live_share"]}
        }
        
        response = await client.post(f"/projects/{project_id}/collaboration-session", json=session_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Collaboration session created"
        assert "session" in data
        
        session = data["session"]
        assert session["project_id"] == project_id
        assert session["created_by"] == str(mock_current_user.id)
        assert session["type"] == "pair_programming"
        assert session["duration_minutes"] == 90

    @pytest.mark.asyncio
    async def test_get_collaboration_insights_success(self, client, mock_current_user):
        """Test getting collaboration insights."""
        project_id = str(uuid4())
        
        with patch('app.api.collaboration.detect_project_conflicts') as mock_detect_conflicts:
            with patch('app.api.collaboration.find_collaboration_opportunities') as mock_find_opps:
                mock_detect_conflicts.return_value = [
                    ConflictDetection(
                        type="concurrent_editing",
                        users=["user1", "user2"],
                        location="src/main.py",
                        description="Conflict",
                        severity="high"
                    )
                ]
                
                mock_find_opps.return_value = [
                    CollaborationOpportunity(
                        type="same_file",
                        users=["user1", "user2"],
                        location="src/utils.py",
                        description="Opportunity",
                        priority=ActivityPriority.MEDIUM,
                        metadata={}
                    )
                ]
                
                response = await client.get(f"/projects/{project_id}/collaboration-insights")
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["project_id"] == project_id
                assert data["current_status"]["active_conflicts"] == 1
                assert data["current_status"]["collaboration_opportunities"] == 1
                assert "recommendations" in data
                assert "trends" in data
                assert "metrics" in data

    @pytest.mark.asyncio
    async def test_get_smart_collaboration_suggestions_success(self, client, mock_current_user):
        """Test getting smart collaboration suggestions."""
        project_id = str(uuid4())
        
        with patch('app.api.collaboration.detect_project_conflicts') as mock_detect_conflicts:
            with patch('app.api.collaboration.find_collaboration_opportunities') as mock_find_opps:
                # Mock conflicts involving current user
                mock_detect_conflicts.return_value = [
                    ConflictDetection(
                        type="concurrent_editing",
                        users=[str(mock_current_user.id), "user2"],
                        location="src/main.py",
                        description="Conflict",
                        severity="high"
                    )
                ]
                
                # Mock opportunities involving current user
                mock_find_opps.return_value = [
                    CollaborationOpportunity(
                        type="same_file",
                        users=[str(mock_current_user.id), "user2"],
                        location="src/utils.py",
                        description="Opportunity",
                        priority=ActivityPriority.HIGH,
                        metadata={}
                    )
                ]
                
                request_data = {
                    "project_id": project_id,
                    "current_activity": {"activity_type": "coding", "location": "src/main.py"},
                    "preferences": {"collaboration_style": "pair_programming"}
                }
                
                response = await client.post("/collaboration/smart-suggestions", json=request_data)
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["user_id"] == str(mock_current_user.id)
                assert data["project_id"] == project_id
                assert "suggestions" in data
                
                suggestions = data["suggestions"]
                assert "immediate_actions" in suggestions
                assert "collaboration_matches" in suggestions
                assert len(suggestions["immediate_actions"]) >= 1  # Should have conflict resolution
                assert len(suggestions["collaboration_matches"]) >= 1  # Should have opportunity

    @pytest.mark.asyncio
    async def test_get_smart_suggestions_missing_project_id(self, client, mock_current_user):
        """Test smart suggestions with missing project_id."""
        request_data = {"current_activity": {"activity_type": "coding"}}
        
        response = await client.post("/collaboration/smart-suggestions", json=request_data)
        
        # Verify bad request
        assert response.status_code == 400
        assert "project_id required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_collaboration_system_stats_success(self, client, mock_admin_user):
        """Test getting collaboration system stats (admin only)."""
        with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
            with patch('app.api.collaboration.conflict_detector') as mock_detector:
                mock_stats = {
                    "is_running": True,
                    "total_recent_conflicts": 5,
                    "total_collaboration_opportunities": 8,
                    "monitored_projects": 3
                }
                mock_detector.get_stats.return_value = mock_stats
                
                response = await client.get("/collaboration/stats")
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["stats"] == mock_stats
                assert data["system_health"] == "operational"

    @pytest.mark.asyncio
    async def test_get_collaboration_stats_access_denied(self, client, mock_current_user):
        """Test collaboration stats access denied for non-admin."""
        response = await client.get("/collaboration/stats")
        
        # Verify access denied
        assert response.status_code == 403
        assert "Admin access required" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_configure_collaboration_settings_success(self, client, mock_admin_user):
        """Test configuring collaboration settings (admin only)."""
        with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
            with patch('app.api.collaboration.conflict_detector') as mock_detector:
                mock_detector.conflict_detection_window_minutes = 30
                mock_detector.collaboration_window_minutes = 120
                mock_detector.file_proximity_threshold = 3
                
                settings = {
                    "conflict_detection_window_minutes": 45,
                    "collaboration_window_minutes": 180,
                    "file_proximity_threshold": 5
                }
                
                response = await client.post("/collaboration/configure", json=settings)
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["settings"]["conflict_detection_window_minutes"] == 45
                assert data["settings"]["collaboration_window_minutes"] == 180
                assert data["settings"]["file_proximity_threshold"] == 5

    @pytest.mark.asyncio
    async def test_configure_collaboration_settings_invalid_values(self, client, mock_admin_user):
        """Test configuring collaboration settings with invalid values."""
        with patch('app.core.deps.get_current_user', return_value=mock_admin_user):
            settings = {"conflict_detection_window_minutes": 200}  # Too high
            
            response = await client.post("/collaboration/configure", json=settings)
            
            # Verify validation error
            assert response.status_code == 400
            assert "must be between 5 and 120" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_collaboration_health_check_healthy(self, client):
        """Test collaboration health check when system is healthy."""
        with patch('app.api.collaboration.conflict_detector') as mock_detector:
            mock_stats = {
                "is_running": True,
                "total_recent_conflicts": 3,
                "total_collaboration_opportunities": 5,
                "monitored_projects": 2
            }
            mock_detector.get_stats.return_value = mock_stats
            
            response = await client.get("/collaboration/health")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["stats"] == mock_stats
            assert data["features"]["conflict_detection"] is True

    @pytest.mark.asyncio
    async def test_collaboration_health_check_degraded(self, client):
        """Test collaboration health check when system is degraded."""
        with patch('app.api.collaboration.conflict_detector') as mock_detector:
            mock_stats = {
                "is_running": False,
                "total_recent_conflicts": 15,  # High conflict count
                "total_collaboration_opportunities": 2,
                "monitored_projects": 1
            }
            mock_detector.get_stats.return_value = mock_stats
            
            response = await client.get("/collaboration/health")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert len(data["issues"]) > 0
            assert data["features"]["conflict_detection"] is False

    @pytest.mark.asyncio
    async def test_collaboration_health_check_error(self, client):
        """Test collaboration health check when error occurs."""
        with patch('app.api.collaboration.conflict_detector') as mock_detector:
            mock_detector.get_stats.side_effect = Exception("System error")
            
            response = await client.get("/collaboration/health")
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "System error" in data["error"]
            assert all(not feature for feature in data["features"].values())


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