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
from app.core.security import get_password_hash


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

        # Insert demo user (upsert) — use enum *names* so SQLAlchemy Enum maps correctly
        # Seed a test user with a hashed password so frontend tests can login
        hashed = get_password_hash('password123')
        await conn.execute(text(
            """
            INSERT INTO users (id, email, name, hashed_password, avatar, role, status, last_activity, preferences, created_at, updated_at)
            VALUES (:id, :email, :name, :pwd, :avatar, :role, :status, :last_activity, :prefs, :now, :now)
            ON CONFLICT (email) DO UPDATE
            SET hashed_password = EXCLUDED.hashed_password,
                name = EXCLUDED.name,
                avatar = COALESCE(EXCLUDED.avatar, users.avatar),
                role = EXCLUDED.role,
                status = EXCLUDED.status,
                last_activity = EXCLUDED.last_activity,
                preferences = EXCLUDED.preferences,
                updated_at = EXCLUDED.updated_at
            """
        ), {
            "id": user_id,
            "email": "test@example.com",
            "name": "Demo User",
            "pwd": hashed,
            "avatar": None,
            # Use enum NAMES (uppercase) to match SQLAlchemy Enum mapping
            "role": "ADMIN",
            "status": "ONLINE",
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
        # Ensure project member role uses enum NAME
        await conn.execute(text(
            """
            INSERT INTO project_members (id, project_id, user_id, role, joined_at, updated_at)
            VALUES (:id, :project_id, :user_id, :role, :now, :now)
            ON CONFLICT (project_id, user_id) DO UPDATE
            SET role = EXCLUDED.role,
                updated_at = EXCLUDED.updated_at
            """
        ), {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "user_id": user_id,
            "role": "OWNER",
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

        # Optionally seed a demo repository and work items if tables exist
        # Create minimal demo tables when running in DEBUG mode so the
        # seeder can populate example repositories and work items without
        # requiring full migrations. This is safe because it only runs in
        # development (settings.DEBUG) and uses CREATE TABLE IF NOT EXISTS.
        if settings.DEBUG:
            # repositories table (minimal subset used by the frontend)
            await conn.execute(text(
                """
                CREATE TABLE IF NOT EXISTS repositories (
                    id UUID PRIMARY KEY,
                    project_id UUID,
                    name TEXT,
                    url TEXT,
                    provider TEXT,
                    branch TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    deployment_config JSONB,
                    created_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
                """
            ))

            # work_items table (minimal subset used by the frontend)
            await conn.execute(text(
                """
                CREATE TABLE IF NOT EXISTS work_items (
                    id UUID PRIMARY KEY,
                    project_id UUID,
                    title TEXT,
                    description TEXT,
                    status TEXT,
                    assignee_id UUID,
                    repository_url TEXT,
                    external_id TEXT,
                    created_at TIMESTAMP WITH TIME ZONE,
                    updated_at TIMESTAMP WITH TIME ZONE
                )
                """
            ))

        if await table_exists(conn, 'repositories'):
            await conn.execute(text(
                """
                INSERT INTO repositories (id, project_id, name, url, provider, branch, is_active, deployment_config, created_at, updated_at)
                VALUES (:id, :project_id, :name, :url, :provider, :branch, true, CAST(:config AS jsonb), :now, :now)
                ON CONFLICT (id) DO NOTHING
                """
            ), {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "name": "demo-repo",
                "url": "https://github.com/example/demo-repo",
                "provider": "github",
                "branch": "main",
                "config": '{"auto_deploy": true, "build_command":"npm run build", "output_directory":"dist", "environment_variables":{}}',
                "now": now
            })

        if await table_exists(conn, 'work_items'):
            await conn.execute(text(
                """
                INSERT INTO work_items (id, project_id, title, description, status, assignee_id, repository_url, created_at, updated_at)
                VALUES (:id, :project_id, :title, :desc, :status, :assignee_id, :repo, :now, :now)
                ON CONFLICT (id) DO NOTHING
                """
            ), {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "title": "Implement demo feature",
                "desc": "Implement the demo work item to show in UI",
                "status": "todo",
                "assignee_id": user_id,
                "repo": "https://github.com/example/demo-repo",
                "now": now
            })

            await conn.execute(text(
                """
                INSERT INTO work_items (id, project_id, title, description, status, assignee_id, repository_url, created_at, updated_at)
                VALUES (:id, :project_id, :title, :desc, :status, :assignee_id, :repo, :now, :now)
                ON CONFLICT (id) DO NOTHING
                """
            ), {
                "id": str(uuid.uuid4()),
                "project_id": project_id,
                "title": "Review pull request",
                "desc": "Review the open PR for the feature branch",
                "status": "in_progress",
                "assignee_id": user_id,
                "repo": "https://github.com/example/demo-repo",
                "now": now
            })

        print("Seeded demo data: demo user, project, project member, activities, repos (if present), and work_items (if present)")


def main():
    print("Seeding demo data using DATABASE_URL:", settings.DATABASE_URL)
    asyncio.run(seed())


if __name__ == '__main__':
    main()
