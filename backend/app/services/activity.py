"""Activity tracking service for managing user activities and presence."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc
from sqlalchemy.orm import selectinload

from app.models.activity import Activity, UserPresence, ActivitySummary, ActivityType, ActivityPriority
from app.models.user import User
from app.models.project import Project
from app.schemas.activity import (
    ActivityCreate, ActivityUpdate, ActivityFilter, ActivityStats,
    UserPresenceCreate, UserPresenceUpdate, PresenceFilter,
    CollaborationOpportunity, ConflictDetection, ActivityBatch
)
from app.core.exceptions import NotFoundError, ValidationError


class ActivityService:
    """Service for managing user activities and tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_activity(self, user_id: str, activity_data: ActivityCreate) -> Activity:
        """
        Create a new activity record.
        
        Args:
            user_id: ID of the user performing the activity
            activity_data: Activity creation data
            
        Returns:
            Created activity record
        """
        # Validate user exists
        user_query = select(User).where(User.id == UUID(user_id))
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        if not user:
            raise NotFoundError(f"User with ID {user_id} not found")

        # Validate project exists if provided
        if activity_data.project_id:
            project_query = select(Project).where(Project.id == UUID(activity_data.project_id))
            project_result = await self.db.execute(project_query)
            project = project_result.scalar_one_or_none()
            if not project:
                raise NotFoundError(f"Project with ID {activity_data.project_id} not found")

        # Create activity
        activity = Activity(
            type=activity_data.type.value,
            title=activity_data.title,
            description=activity_data.description,
            location=activity_data.location,
            user_id=UUID(user_id),
            project_id=UUID(activity_data.project_id) if activity_data.project_id else None,
            priority=activity_data.priority.value,
            metadata=activity_data.metadata or {},
            related_file_id=UUID(activity_data.related_file_id) if activity_data.related_file_id else None,
            related_deployment_id=UUID(activity_data.related_deployment_id) if activity_data.related_deployment_id else None,
            started_at=activity_data.started_at or datetime.utcnow(),
            duration_seconds=str(activity_data.duration_seconds) if activity_data.duration_seconds else None
        )

        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)

        return activity

    async def update_activity(self, activity_id: str, user_id: str, activity_data: ActivityUpdate) -> Activity:
        """
        Update an existing activity.
        
        Args:
            activity_id: ID of the activity to update
            user_id: ID of the user updating the activity
            activity_data: Activity update data
            
        Returns:
            Updated activity record
        """
        # Get activity
        query = select(Activity).where(
            and_(Activity.id == UUID(activity_id), Activity.user_id == UUID(user_id))
        )
        result = await self.db.execute(query)
        activity = result.scalar_one_or_none()
        
        if not activity:
            raise NotFoundError(f"Activity with ID {activity_id} not found or access denied")

        # Update fields
        if activity_data.title is not None:
            activity.title = activity_data.title
        if activity_data.description is not None:
            activity.description = activity_data.description
        if activity_data.location is not None:
            activity.location = activity_data.location
        if activity_data.priority is not None:
            activity.priority = activity_data.priority.value
        if activity_data.metadata is not None:
            activity.metadata = activity_data.metadata
        if activity_data.ended_at is not None:
            activity.ended_at = activity_data.ended_at
        if activity_data.duration_seconds is not None:
            activity.duration_seconds = str(activity_data.duration_seconds)

        await self.db.commit()
        await self.db.refresh(activity)

        return activity

    async def get_activities(self, filters: ActivityFilter) -> List[Activity]:
        """
        Get activities based on filters.
        
        Args:
            filters: Activity filter criteria
            
        Returns:
            List of activities matching the filters
        """
        query = select(Activity).options(
            selectinload(Activity.user),
            selectinload(Activity.project)
        )

        # Apply filters
        conditions = []
        
        if filters.user_id:
            conditions.append(Activity.user_id == UUID(filters.user_id))
        
        if filters.project_id:
            conditions.append(Activity.project_id == UUID(filters.project_id))
        
        if filters.activity_types:
            type_values = [t.value for t in filters.activity_types]
            conditions.append(Activity.type.in_(type_values))
        
        if filters.location:
            conditions.append(Activity.location.ilike(f"%{filters.location}%"))
        
        if filters.priority:
            conditions.append(Activity.priority == filters.priority.value)
        
        if filters.start_date:
            conditions.append(Activity.created_at >= filters.start_date)
        
        if filters.end_date:
            conditions.append(Activity.created_at <= filters.end_date)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by creation date (newest first)
        query = query.order_by(desc(Activity.created_at))
        
        # Apply pagination
        query = query.offset(filters.offset).limit(filters.limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_activity_stats(self, user_id: Optional[str] = None, project_id: Optional[str] = None, days: int = 30) -> ActivityStats:
        """
        Get activity statistics.
        
        Args:
            user_id: Optional user ID to filter by
            project_id: Optional project ID to filter by
            days: Number of days to analyze
            
        Returns:
            Activity statistics
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query
        query = select(Activity).where(Activity.created_at >= start_date)
        
        if user_id:
            query = query.where(Activity.user_id == UUID(user_id))
        if project_id:
            query = query.where(Activity.project_id == UUID(project_id))

        result = await self.db.execute(query)
        activities = result.scalars().all()

        # Calculate statistics
        total_activities = len(activities)
        
        activities_by_type = {}
        activities_by_priority = {}
        location_counts = {}
        
        for activity in activities:
            # Count by type
            activities_by_type[activity.type] = activities_by_type.get(activity.type, 0) + 1
            
            # Count by priority
            activities_by_priority[activity.priority] = activities_by_priority.get(activity.priority, 0) + 1
            
            # Count by location
            if activity.location:
                location_counts[activity.location] = location_counts.get(activity.location, 0) + 1

        # Most active locations
        most_active_locations = [
            {"location": loc, "count": count}
            for loc, count in sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        # Activity timeline (daily counts)
        timeline = {}
        for activity in activities:
            date_key = activity.created_at.date().isoformat()
            timeline[date_key] = timeline.get(date_key, 0) + 1

        activity_timeline = [
            {"date": date, "count": count}
            for date, count in sorted(timeline.items())
        ]

        return ActivityStats(
            total_activities=total_activities,
            activities_by_type=activities_by_type,
            activities_by_priority=activities_by_priority,
            most_active_locations=most_active_locations,
            activity_timeline=activity_timeline,
            collaboration_metrics={
                "unique_locations": len(location_counts),
                "average_activities_per_day": total_activities / max(days, 1),
                "most_active_day": max(timeline.items(), key=lambda x: x[1])[0] if timeline else None
            }
        )

    async def create_batch_activities(self, user_id: str, batch_data: ActivityBatch) -> List[Activity]:
        """
        Create multiple activities in a batch.
        
        Args:
            user_id: ID of the user creating activities
            batch_data: Batch activity data
            
        Returns:
            List of created activities
        """
        activities = []
        
        for activity_data in batch_data.activities:
            activity = await self.create_activity(user_id, activity_data)
            activities.append(activity)

        return activities

    async def end_activity(self, activity_id: str, user_id: str) -> Activity:
        """
        End an ongoing activity.
        
        Args:
            activity_id: ID of the activity to end
            user_id: ID of the user ending the activity
            
        Returns:
            Updated activity record
        """
        # Get activity
        query = select(Activity).where(
            and_(Activity.id == UUID(activity_id), Activity.user_id == UUID(user_id))
        )
        result = await self.db.execute(query)
        activity = result.scalar_one_or_none()
        
        if not activity:
            raise NotFoundError(f"Activity with ID {activity_id} not found or access denied")

        # End the activity
        now = datetime.utcnow()
        activity.ended_at = now
        
        # Calculate duration if started_at exists
        if activity.started_at:
            duration = (now - activity.started_at).total_seconds()
            activity.duration_seconds = str(int(duration))

        await self.db.commit()
        await self.db.refresh(activity)

        return activity


class PresenceService:
    """Service for managing user presence and real-time status."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_presence(self, user_id: str, presence_data: UserPresenceCreate) -> UserPresence:
        """
        Update or create user presence.
        
        Args:
            user_id: ID of the user
            presence_data: Presence data
            
        Returns:
            Updated presence record
        """
        # Check if presence record exists
        query = select(UserPresence).where(
            and_(
                UserPresence.user_id == UUID(user_id),
                UserPresence.project_id == UUID(presence_data.project_id) if presence_data.project_id else UserPresence.project_id.is_(None)
            )
        )
        result = await self.db.execute(query)
        presence = result.scalar_one_or_none()

        now = datetime.utcnow()

        if presence:
            # Update existing presence
            presence.status = presence_data.status.value
            presence.current_location = presence_data.current_location
            presence.current_activity = presence_data.current_activity.value if presence_data.current_activity else None
            presence.last_seen = now
            presence.last_activity = now
            if presence_data.metadata:
                presence.metadata.update(presence_data.metadata)
        else:
            # Create new presence record
            presence = UserPresence(
                user_id=UUID(user_id),
                project_id=UUID(presence_data.project_id) if presence_data.project_id else None,
                status=presence_data.status.value,
                current_location=presence_data.current_location,
                current_activity=presence_data.current_activity.value if presence_data.current_activity else None,
                session_id=presence_data.session_id,
                ip_address=presence_data.ip_address,
                user_agent=presence_data.user_agent,
                last_seen=now,
                session_started=now,
                last_activity=now,
                metadata=presence_data.metadata or {}
            )
            self.db.add(presence)

        await self.db.commit()
        await self.db.refresh(presence)

        return presence

    async def get_project_presence(self, project_id: str) -> List[UserPresence]:
        """
        Get all user presence for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of user presence records
        """
        query = select(UserPresence).options(
            selectinload(UserPresence.user)
        ).where(
            UserPresence.project_id == UUID(project_id)
        ).order_by(desc(UserPresence.last_activity))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_online_users(self, project_id: Optional[str] = None) -> List[UserPresence]:
        """
        Get currently online users.
        
        Args:
            project_id: Optional project ID to filter by
            
        Returns:
            List of online user presence records
        """
        # Consider users online if they were active in the last 5 minutes
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        
        query = select(UserPresence).options(
            selectinload(UserPresence.user)
        ).where(
            and_(
                UserPresence.status.in_(["online", "active"]),
                UserPresence.last_activity >= cutoff_time
            )
        )

        if project_id:
            query = query.where(UserPresence.project_id == UUID(project_id))

        query = query.order_by(desc(UserPresence.last_activity))

        result = await self.db.execute(query)
        return result.scalars().all()

    async def detect_collaboration_opportunities(self, user_id: str, project_id: str) -> List[CollaborationOpportunity]:
        """
        Detect collaboration opportunities for a user.
        
        Args:
            user_id: User ID
            project_id: Project ID
            
        Returns:
            List of collaboration opportunities
        """
        opportunities = []
        
        # Get current user's recent activities
        recent_activities = await self._get_recent_activities(user_id, project_id, hours=2)
        user_locations = {activity.location for activity in recent_activities if activity.location}
        
        # Get other users' recent activities in the same project
        other_users_query = select(Activity).options(
            selectinload(Activity.user)
        ).where(
            and_(
                Activity.project_id == UUID(project_id),
                Activity.user_id != UUID(user_id),
                Activity.created_at >= datetime.utcnow() - timedelta(hours=2)
            )
        )
        
        result = await self.db.execute(other_users_query)
        other_activities = result.scalars().all()
        
        # Group by user
        user_activities = {}
        for activity in other_activities:
            if activity.user_id not in user_activities:
                user_activities[activity.user_id] = []
            user_activities[activity.user_id].append(activity)
        
        # Find opportunities
        for other_user_id, activities in user_activities.items():
            other_locations = {activity.location for activity in activities if activity.location}
            
            # Same file collaboration
            common_locations = user_locations.intersection(other_locations)
            if common_locations:
                for location in common_locations:
                    opportunities.append(CollaborationOpportunity(
                        type="same_file",
                        users=[user_id, str(other_user_id)],
                        location=location,
                        description=f"Both users are working on {location}",
                        priority=ActivityPriority.HIGH,
                        metadata={"common_locations": list(common_locations)}
                    ))
            
            # Related files (same directory or similar names)
            for user_loc in user_locations:
                for other_loc in other_locations:
                    if user_loc != other_loc and self._are_related_locations(user_loc, other_loc):
                        opportunities.append(CollaborationOpportunity(
                            type="related_files",
                            users=[user_id, str(other_user_id)],
                            location=f"{user_loc} & {other_loc}",
                            description=f"Working on related files: {user_loc} and {other_loc}",
                            priority=ActivityPriority.MEDIUM,
                            metadata={"user_location": user_loc, "other_location": other_loc}
                        ))

        return opportunities

    async def detect_conflicts(self, project_id: str) -> List[ConflictDetection]:
        """
        Detect potential conflicts in a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Get recent activities (last 30 minutes)
        recent_time = datetime.utcnow() - timedelta(minutes=30)
        query = select(Activity).options(
            selectinload(Activity.user)
        ).where(
            and_(
                Activity.project_id == UUID(project_id),
                Activity.created_at >= recent_time,
                Activity.location.isnot(None)
            )
        )
        
        result = await self.db.execute(query)
        activities = result.scalars().all()
        
        # Group by location
        location_activities = {}
        for activity in activities:
            if activity.location not in location_activities:
                location_activities[activity.location] = []
            location_activities[activity.location].append(activity)
        
        # Detect concurrent editing
        for location, location_acts in location_activities.items():
            # Group by user
            user_activities = {}
            for activity in location_acts:
                if activity.user_id not in user_activities:
                    user_activities[activity.user_id] = []
                user_activities[activity.user_id].append(activity)
            
            # If multiple users are working on the same location
            if len(user_activities) > 1:
                user_ids = list(user_activities.keys())
                conflicts.append(ConflictDetection(
                    type="concurrent_editing",
                    users=[str(uid) for uid in user_ids],
                    location=location,
                    description=f"Multiple users editing {location} simultaneously",
                    severity="high" if len(user_ids) > 2 else "medium",
                    suggested_resolution="Consider coordinating changes or using version control",
                    metadata={
                        "user_count": len(user_ids),
                        "activity_count": len(location_acts),
                        "time_window": "30 minutes"
                    }
                ))

        return conflicts

    async def cleanup_stale_presence(self, hours: int = 24) -> int:
        """
        Clean up stale presence records.
        
        Args:
            hours: Hours after which presence is considered stale
            
        Returns:
            Number of cleaned up records
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Update stale presence to offline
        query = select(UserPresence).where(
            and_(
                UserPresence.last_activity < cutoff_time,
                UserPresence.status != "offline"
            )
        )
        
        result = await self.db.execute(query)
        stale_records = result.scalars().all()
        
        count = 0
        for record in stale_records:
            record.status = "offline"
            count += 1
        
        await self.db.commit()
        return count

    async def _get_recent_activities(self, user_id: str, project_id: str, hours: int = 2) -> List[Activity]:
        """Get recent activities for a user in a project."""
        recent_time = datetime.utcnow() - timedelta(hours=hours)
        query = select(Activity).where(
            and_(
                Activity.user_id == UUID(user_id),
                Activity.project_id == UUID(project_id),
                Activity.created_at >= recent_time
            )
        )
        
        result = await self.db.execute(query)
        return result.scalars().all()

    def _are_related_locations(self, loc1: str, loc2: str) -> bool:
        """Check if two locations are related (same directory, similar names, etc.)."""
        if not loc1 or not loc2:
            return False
        
        # Same directory
        if "/" in loc1 and "/" in loc2:
            dir1 = "/".join(loc1.split("/")[:-1])
            dir2 = "/".join(loc2.split("/")[:-1])
            if dir1 == dir2:
                return True
        
        # Similar file names (edit distance or common prefix)
        if len(loc1) > 3 and len(loc2) > 3:
            # Simple similarity check - common prefix of at least 3 characters
            common_prefix_len = 0
            for i in range(min(len(loc1), len(loc2))):
                if loc1[i] == loc2[i]:
                    common_prefix_len += 1
                else:
                    break
            
            if common_prefix_len >= 3:
                return True
        
        return False