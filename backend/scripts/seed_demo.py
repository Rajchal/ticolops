"""Lightweight SQL-based seeder for demo purposes.

This seeder avoids importing ORM model classes (which can trigger mapper
configuration issues for partially implemented models). It expects the
database schema to already exist (run Alembic migrations first). If tables
are missing, it will print a helpful message.

Run after starting services with docker-compose (or after running migrations).
"""

import asyncio
import uuid
from datetime import datetime

from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine


async def table_exists(conn, table_name: str) -> bool:
    q = text("SELECT to_regclass(:t) IS NOT NULL AS exists")
    res = await conn.execute(q.bindparams(t=table_name))
    row = res.first()
    return bool(row and row[0])


async def seed():
    async with engine.begin() as conn:
        # Check for required tables
        required = ["users", "projects", "project_members", "activities"]
        missing = []
        for t in required:
            exists = await table_exists(conn, t)
            if not exists:
                missing.append(t)

        if missing:
            print("The following tables are missing:", missing)
            print("Please run migrations (alembic upgrade head) before seeding.")
            return

        user_id = str(uuid.uuid4())
        project_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Insert demo user
        await conn.execute(text(
            """
            INSERT INTO users (id, email, name, hashed_password, role, status, last_activity, preferences, created_at, updated_at)
            VALUES (:id, :email, :name, :pwd, :role, :status, :last_activity, :prefs, :now, :now)
            ON CONFLICT (email) DO NOTHING
            """
        ), {
            "id": user_id,
            "email": "demo@ticolops.local",
            "name": "Demo User",
            "pwd": "not_used_in_demo",
            "role": "admin",
            "status": "online",
            "last_activity": now,
            "prefs": "{}",
            "now": now
        })

        # Insert demo project
        await conn.execute(text(
            """
            INSERT INTO projects (id, name, description, owner_id, created_at, updated_at)
            VALUES (:id, :name, :desc, :owner_id, :now, :now)
            ON CONFLICT (id) DO NOTHING
            """
        ), {
            "id": project_id,
            "name": "Demo Project",
            "desc": "Project used for hackathon demo",
            "owner_id": user_id,
            "now": now
        })

        # Insert project member
        await conn.execute(text(
            """
            INSERT INTO project_members (id, project_id, user_id, role, joined_at, updated_at)
            VALUES (:id, :project_id, :user_id, :role, :now, :now)
            ON CONFLICT (project_id, user_id) DO NOTHING
            """
        ), {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "user_id": user_id,
            "role": "owner",
            "now": now
        })

        # Insert a couple of activities
        await conn.execute(text(
            """
            INSERT INTO activities (id, type, title, description, user_id, project_id, location, meta_data, priority, created_at)
            VALUES (:id, :type, :title, :desc, :user_id, :project_id, :loc, :meta, :priority, :now)
            ON CONFLICT (id) DO NOTHING
            """
        ), {
            "id": str(uuid.uuid4()),
            "type": "file_created",
            "title": "Created README.md",
            "desc": "Initial README for demo",
            "user_id": user_id,
            "project_id": project_id,
            "loc": "README.md",
            "meta": "{}",
            "priority": "medium",
            "now": now
        })

        await conn.execute(text(
            """
            INSERT INTO activities (id, type, title, description, user_id, project_id, location, meta_data, priority, created_at)
            VALUES (:id, :type, :title, :desc, :user_id, :project_id, :loc, :meta, :priority, :now)
            ON CONFLICT (id) DO NOTHING
            """
        ), {
            "id": str(uuid.uuid4()),
            "type": "comment_added",
            "title": "Added comment to proposal",
            "desc": "Great work!",
            "user_id": user_id,
            "project_id": project_id,
            "loc": "proposal.md",
            "meta": "{}",
            "priority": "low",
            "now": now
        })

        print("Seeded demo data: demo user, project, project member, and activities")


def main():
    print("Seeding demo data using DATABASE_URL:", settings.DATABASE_URL)
    asyncio.run(seed())


if __name__ == '__main__':
    main()
