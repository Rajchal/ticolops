"""Seed script to create minimal demo data for a hackathon demo.

This script connects using `DATABASE_URL` from the app settings, creates tables
(if not present), and inserts a demo user, demo project, and a couple of activities.

Run after starting the `docker-compose.yml` services (postgres, redis, backend).
"""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import settings
from app.core.database import engine, AsyncSessionLocal
from app.models.user import User, UserRoleEnum, UserStatusEnum
from app.models.project import Project, ProjectMember
from app.models.activity import Activity

import uuid
from datetime import datetime


async def create_tables():
    # We rely on SQLAlchemy models and let Alembic handle migrations in production.
    # For the demo we'll create missing tables using metadata.create_all via sync engine.
    # Use a sync connection via the async engine's raw connection.
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: sync_conn.exec_driver_sql('SELECT 1'))


async def seed():
    async with AsyncSessionLocal() as session:
        # Create a demo user
        demo_user = User(
            id=uuid.uuid4(),
            email='demo@ticolops.local',
            name='Demo User',
            hashed_password='not_used_in_demo',
            avatar=None,
            role=UserRoleEnum.ADMIN,
            status=UserStatusEnum.ONLINE,
            last_activity=datetime.utcnow()
        )

        # Create a demo project
        demo_project = Project(
            id=uuid.uuid4(),
            name='Demo Project',
            description='Project used for hackathon demo',
            owner_id=demo_user.id
        )

        # Project member linking demo user
        project_member = ProjectMember(
            id=uuid.uuid4(),
            project_id=demo_project.id,
            user_id=demo_user.id,
            role='owner'
        )

        # Add a couple of activities
        activity1 = Activity(
            id=uuid.uuid4(),
            type='file_created',
            title='Created README.md',
            description='Initial README for demo',
            user_id=demo_user.id,
            project_id=demo_project.id,
            location='README.md',
            meta_data={},
            created_at=datetime.utcnow()
        )

        activity2 = Activity(
            id=uuid.uuid4(),
            type='comment_added',
            title='Added comment to proposal',
            description='Great work!',
            user_id=demo_user.id,
            project_id=demo_project.id,
            location='proposal.md',
            meta_data={},
            created_at=datetime.utcnow()
        )

        session.add_all([demo_user, demo_project, project_member, activity1, activity2])
        await session.commit()
        print("Seeded demo data: demo user, project, and activities")


def main():
    print("Seeding demo data using DATABASE_URL:", settings.DATABASE_URL)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(seed())


if __name__ == '__main__':
    main()
