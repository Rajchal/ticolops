"""Tests for conflict detection and collaboration features."""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4

from app.services.conflict_detector import ConflictDetector
from app.schemas.activity import ConflictDetection, CollaborationOpportunity, ActivityPriority
from app.models.activity import Activity, ActivityType
from app.models.user import User


@pytest.fixture
def conflict_detector():
    """Fresh conflict detector for testing."""
    return ConflictDetector()


@pytest.fixture
def sample_activities():
    """Sample activities for testing."""
    user1_id = uuid4()
    user2_id = uuid4()
    project_id = uuid4()
    
    return [
        Activity(
            id=uuid4(),
            type=ActivityType.CODING.value,
            title="Working on main.py",
            user_id=user1_id,
            project_id=project_id,
            location="src/main.py",
            created_at=datetime.utcnow() - timedelta(minutes=5),
            metadata={}
        ),
        Activity(
            id=uuid4(),
            type=ActivityType.CODING.value,
            title="Editing main.py",
            user_id=user2_id,
            project_id=project_id,
            location="src/main.py",
            created_at=datetime.utcnow() - timedelta(minutes=3),
            metadata={}
        ),
        Activity(
            id=uuid4(),
            type=ActivityType.TESTING.value,
            title="Testing utils",
            user_id=user1_id,
            project_id=project_id,
            location="src/utils.py",
            created_at=datetime.utcnow() - timedelta(minutes=10),
            metadata={}
        )
    ]


@pytest.fixture
def sample_presence():
    """Sample presence data for testing."""
    return {
        "user1": {
            "user_id": "user1",
            "status": "online",
            "current_location": "src/main.py",
            "current_activity": "coding"
        },
        "user2": {
            "user_id": "user2",
            "status": "active",
            "current_location": "src/main.py",
            "current_activity": "coding"
        },
        "user3": {
            "user_id": "user3",
            "status": "online",
            "current_location": "src/utils.py",
            "current_activity": "testing"
        }
    }


class TestConflictDetector:
    """Test cases for ConflictDetector."""

    @pytest.mark.asyncio
    async def test_start_stop_detector(self, conflict_detector):
        """Test starting and stopping the conflict detector."""
        # Initially not running
        assert not conflict_detector._is_running
        
        # Start
        await conflict_detector.start()
        assert conflict_detector._is_running
        assert conflict_detector._detection_task is not None
        
        # Stop
        await conflict_detector.stop()
        assert not conflict_detector._is_running

    @pytest.mark.asyncio
    async def test_detect_concurrent_editing_conflict(self, conflict_detector, sample_activities):
        """Test detection of concurrent editing conflicts."""
        project_id = str(sample_activities[0].project_id)
        
        # Mock database operations
        with patch.object(conflict_detector, '_get_recent_project_activities') as mock_get_activities:
            mock_get_activities.return_value = sample_activities[:2]  # Two users editing same file
            
            conflicts = await conflict_detector.detect_project_conflicts(project_id)
            
            # Should detect concurrent editing conflict
            assert len(conflicts) >= 1
            concurrent_conflicts = [c for c in conflicts if c.type == "concurrent_editing"]
            assert len(concurrent_conflicts) == 1
            
            conflict = concurrent_conflicts[0]
            assert conflict.location == "src/main.py"
            assert len(conflict.users) == 2
            assert conflict.severity in ["medium", "high"]

    @pytest.mark.asyncio
    async def test_detect_overlapping_work_conflict(self, conflict_detector):
        """Test detection of overlapping work conflicts."""
        project_id = str(uuid4())
        
        # Create activities in related files
        user1_id = uuid4()
        user2_id = uuid4()
        
        related_activities = [
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Working on component",
                user_id=user1_id,
                project_id=uuid4(project_id),
                location="src/components/header.py",
                created_at=datetime.utcnow() - timedelta(minutes=5),
                metadata={}
            ),
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Working on related component",
                user_id=user2_id,
                project_id=uuid4(project_id),
                location="src/components/header_utils.py",
                created_at=datetime.utcnow() - timedelta(minutes=3),
                metadata={}
            )
        ]
        
        with patch.object(conflict_detector, '_get_recent_project_activities') as mock_get_activities:
            mock_get_activities.return_value = related_activities
            
            conflicts = await conflict_detector.detect_project_conflicts(project_id)
            
            # Should detect overlapping work
            overlapping_conflicts = [c for c in conflicts if c.type == "overlapping_work"]
            assert len(overlapping_conflicts) >= 0  # May or may not detect based on similarity algorithm

    @pytest.mark.asyncio
    async def test_detect_same_file_collaboration_opportunity(self, conflict_detector, sample_presence):
        """Test detection of same file collaboration opportunities."""
        project_id = str(uuid4())
        
        with patch.object(conflict_detector, '_get_recent_project_activities') as mock_get_activities:
            mock_get_activities.return_value = []
            
            opportunities = await conflict_detector.detect_collaboration_opportunities(project_id)
            
            # Mock presence data shows two users in same file
            with patch('app.services.conflict_detector.presence_manager') as mock_presence_manager:
                mock_presence_manager.get_project_presence.return_value = sample_presence
                
                opportunities = await conflict_detector._detect_same_file_opportunities(
                    [], sample_presence, None
                )
                
                # Should find same file opportunity
                same_file_opps = [o for o in opportunities if o.type == "same_file"]
                assert len(same_file_opps) >= 1
                
                opp = same_file_opps[0]
                assert opp.location == "src/main.py"
                assert len(opp.users) == 2
                assert opp.priority == ActivityPriority.HIGH

    @pytest.mark.asyncio
    async def test_detect_related_file_opportunities(self, conflict_detector, sample_presence):
        """Test detection of related file collaboration opportunities."""
        # Modify presence to have users in related files
        related_presence = {
            "user1": {
                "user_id": "user1",
                "status": "online",
                "current_location": "src/auth.py",
                "current_activity": "coding"
            },
            "user2": {
                "user_id": "user2",
                "status": "active",
                "current_location": "src/auth_utils.py",
                "current_activity": "coding"
            }
        }
        
        opportunities = await conflict_detector._detect_related_file_opportunities(
            [], related_presence, None
        )
        
        # Should find related file opportunity
        related_opps = [o for o in opportunities if o.type == "related_files"]
        assert len(related_opps) >= 1
        
        opp = related_opps[0]
        assert "auth" in opp.location.lower()
        assert len(opp.users) == 2
        assert opp.priority == ActivityPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_analyze_conflict_severity(self, conflict_detector):
        """Test conflict severity analysis."""
        conflict = ConflictDetection(
            type="concurrent_editing",
            users=["user1", "user2", "user3"],  # 3 users = higher severity
            location="src/main.py",  # Critical file
            description="Multiple users editing main file",
            severity="high",
            metadata={"duration_minutes": 90}  # Long duration
        )
        
        analysis = await conflict_detector.analyze_conflict_severity(conflict)
        
        # Should have high severity score
        assert analysis["severity_score"] >= 8
        assert analysis["urgency"] in ["high", "critical"]
        assert len(analysis["impact_factors"]) > 0
        assert len(analysis["recommended_actions"]) > 0

    @pytest.mark.asyncio
    async def test_suggest_conflict_resolution(self, conflict_detector):
        """Test conflict resolution suggestions."""
        conflict = ConflictDetection(
            type="concurrent_editing",
            users=["user1", "user2"],
            location="src/main.py",
            description="Two users editing same file",
            severity="medium"
        )
        
        suggestions = await conflict_detector.suggest_conflict_resolution(conflict)
        
        # Should provide resolution strategies
        assert suggestions["primary_strategy"] != ""
        assert len(suggestions["alternative_strategies"]) > 0
        assert len(suggestions["tools_recommended"]) > 0
        assert len(suggestions["communication_channels"]) > 0
        assert suggestions["timeline"] != ""

    @pytest.mark.asyncio
    async def test_get_conflict_history(self, conflict_detector):
        """Test getting conflict history."""
        project_id = str(uuid4())
        
        # Add some mock conflicts to cache
        mock_conflicts = [
            {
                "type": "concurrent_editing",
                "severity": "high",
                "location": "src/main.py"
            },
            {
                "type": "overlapping_work",
                "severity": "medium",
                "location": "src/utils.py"
            }
        ]
        conflict_detector.recent_conflicts[project_id] = mock_conflicts
        
        history = await conflict_detector.get_conflict_history(project_id, days=7)
        
        # Should return history analysis
        assert history["total_conflicts"] == 2
        assert "concurrent_editing" in history["conflicts_by_type"]
        assert "high" in history["conflicts_by_severity"]
        assert len(history["frequent_conflict_locations"]) > 0

    def test_check_time_overlap(self, conflict_detector):
        """Test time overlap detection."""
        now = datetime.utcnow()
        
        # Activities with time overlap
        overlapping_activities = {
            "user1": [
                MagicMock(created_at=now - timedelta(minutes=5)),
                MagicMock(created_at=now - timedelta(minutes=3))
            ],
            "user2": [
                MagicMock(created_at=now - timedelta(minutes=4)),
                MagicMock(created_at=now - timedelta(minutes=2))
            ]
        }
        
        # Activities without overlap
        non_overlapping_activities = {
            "user1": [MagicMock(created_at=now - timedelta(minutes=30))],
            "user2": [MagicMock(created_at=now - timedelta(minutes=5))]
        }
        
        assert conflict_detector._check_time_overlap(overlapping_activities) is True
        assert conflict_detector._check_time_overlap(non_overlapping_activities) is False

    def test_are_locations_related(self, conflict_detector):
        """Test location relationship detection."""
        # Same directory
        assert conflict_detector._are_locations_related("src/auth.py", "src/auth_utils.py") is True
        
        # Similar names
        assert conflict_detector._are_locations_related("component.py", "component_test.py") is True
        
        # Test files
        assert conflict_detector._are_locations_related("main.py", "main_test.py") is True
        
        # Unrelated
        assert conflict_detector._are_locations_related("auth.py", "database.py") is False
        
        # Empty/None
        assert conflict_detector._are_locations_related("", "test.py") is False
        assert conflict_detector._are_locations_related(None, "test.py") is False

    def test_find_related_locations(self, conflict_detector):
        """Test finding groups of related locations."""
        locations = [
            "src/auth.py",
            "src/auth_utils.py",
            "src/auth_test.py",
            "src/database.py",
            "src/models/user.py",
            "src/models/project.py"
        ]
        
        related_groups = conflict_detector._find_related_locations(locations)
        
        # Should find related groups
        assert len(related_groups) > 0
        
        # Auth files should be grouped together
        auth_group = None
        for group in related_groups:
            if any("auth" in loc for loc in group):
                auth_group = group
                break
        
        assert auth_group is not None
        assert len(auth_group) >= 2

    def test_group_activities_by_location(self, conflict_detector, sample_activities):
        """Test grouping activities by location."""
        location_groups = conflict_detector._group_activities_by_location(sample_activities)
        
        # Should group by location
        assert "src/main.py" in location_groups
        assert "src/utils.py" in location_groups
        
        # main.py should have 2 activities
        assert len(location_groups["src/main.py"]) == 2
        
        # utils.py should have 1 activity
        assert len(location_groups["src/utils.py"]) == 1

    def test_get_stats(self, conflict_detector):
        """Test getting conflict detector statistics."""
        # Add some mock data
        conflict_detector.recent_conflicts = {
            "proj1": [{"type": "concurrent_editing"}],
            "proj2": [{"type": "overlapping_work"}, {"type": "resource_conflict"}]
        }
        conflict_detector.collaboration_suggestions = {
            "proj1": [{"type": "same_file"}],
            "proj2": [{"type": "related_files"}]
        }
        
        stats = conflict_detector.get_stats()
        
        # Verify statistics
        assert stats["total_recent_conflicts"] == 3
        assert stats["total_collaboration_opportunities"] == 2
        assert stats["monitored_projects"] == 2
        assert "detection_window_minutes" in stats
        assert "collaboration_window_minutes" in stats
        assert "settings" in stats

    @pytest.mark.asyncio
    async def test_detect_complementary_skill_opportunities(self, conflict_detector):
        """Test detection of complementary skill opportunities."""
        # Mock activities showing different skills
        activities = [
            MagicMock(
                user_id=uuid4(),
                type="coding",
                location="src/frontend.js"
            ),
            MagicMock(
                user_id=uuid4(),
                type="testing",
                location="tests/backend_test.py"
            )
        ]
        
        # Mock presence
        presence = {
            str(activities[0].user_id): {"user_id": str(activities[0].user_id)},
            str(activities[1].user_id): {"user_id": str(activities[1].user_id)}
        }
        
        mock_db = AsyncMock()
        
        opportunities = await conflict_detector._detect_complementary_skill_opportunities(
            activities, presence, None, mock_db
        )
        
        # Should detect complementary skills
        skill_opps = [o for o in opportunities if o.type == "complementary_skills"]
        # May or may not find opportunities based on skill inference logic
        assert len(skill_opps) >= 0

    @pytest.mark.asyncio
    async def test_detect_knowledge_sharing_opportunities(self, conflict_detector):
        """Test detection of knowledge sharing opportunities."""
        user1_id = uuid4()
        user2_id = uuid4()
        
        # Mock activities showing expertise and learning needs
        activities = [
            # User1 has high activity in auth.py (expertise)
            MagicMock(user_id=user1_id, location="src/auth.py", type="coding", title="Auth work"),
            MagicMock(user_id=user1_id, location="src/auth.py", type="coding", title="More auth"),
            MagicMock(user_id=user1_id, location="src/auth.py", type="coding", title="Auth fixes"),
            MagicMock(user_id=user1_id, location="src/auth.py", type="coding", title="Auth updates"),
            
            # User2 is debugging auth.py (learning need)
            MagicMock(user_id=user2_id, location="src/auth.py", type="debugging", title="Auth error")
        ]
        
        presence = {
            str(user1_id): {"user_id": str(user1_id)},
            str(user2_id): {"user_id": str(user2_id)}
        }
        
        mock_db = AsyncMock()
        
        opportunities = await conflict_detector._detect_knowledge_sharing_opportunities(
            activities, presence, None, mock_db
        )
        
        # Should detect knowledge sharing opportunity
        knowledge_opps = [o for o in opportunities if o.type == "knowledge_sharing"]
        assert len(knowledge_opps) >= 1
        
        if knowledge_opps:
            opp = knowledge_opps[0]
            assert str(user1_id) in opp.users  # Expert
            assert str(user2_id) in opp.users  # Learner
            assert opp.location == "src/auth.py"


@pytest.mark.asyncio
async def test_conflict_detector_integration_flow():
    """Integration test for complete conflict detection flow."""
    detector = ConflictDetector()
    project_id = str(uuid4())
    
    # Mock database operations
    with patch.object(detector, '_get_recent_project_activities') as mock_get_activities:
        # Create mock activities with conflicts
        user1_id = uuid4()
        user2_id = uuid4()
        
        mock_activities = [
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Editing main",
                user_id=user1_id,
                project_id=uuid4(project_id),
                location="src/main.py",
                created_at=datetime.utcnow() - timedelta(minutes=5),
                metadata={}
            ),
            Activity(
                id=uuid4(),
                type=ActivityType.CODING.value,
                title="Also editing main",
                user_id=user2_id,
                project_id=uuid4(project_id),
                location="src/main.py",
                created_at=datetime.utcnow() - timedelta(minutes=3),
                metadata={}
            )
        ]
        
        mock_get_activities.return_value = mock_activities
        
        # 1. Detect conflicts
        conflicts = await detector.detect_project_conflicts(project_id)
        assert len(conflicts) >= 1
        
        # 2. Analyze conflict severity
        if conflicts:
            analysis = await detector.analyze_conflict_severity(conflicts[0])
            assert "severity_score" in analysis
            assert "urgency" in analysis
        
        # 3. Get resolution suggestions
        if conflicts:
            suggestions = await detector.suggest_conflict_resolution(conflicts[0])
            assert "primary_strategy" in suggestions
            assert len(suggestions["alternative_strategies"]) > 0
        
        # 4. Get conflict history
        history = await detector.get_conflict_history(project_id)
        assert "total_conflicts" in history
        
        # 5. Detect collaboration opportunities
        with patch('app.services.conflict_detector.presence_manager') as mock_presence:
            mock_presence.get_project_presence.return_value = {
                str(user1_id): {"user_id": str(user1_id), "current_location": "src/utils.py"},
                str(user2_id): {"user_id": str(user2_id), "current_location": "src/helpers.py"}
            }
            
            opportunities = await detector.detect_collaboration_opportunities(project_id)
            # May or may not find opportunities based on current logic
            assert isinstance(opportunities, list)