"""Create minimal demo tables if they do not exist.

This script is intentionally small and only creates the columns required by
the demo seeder. It should be safe to run against an empty database. If some
columns or tables already exist (from partial migrations), the CREATE TABLE IF
NOT EXISTS statements will skip existing tables.
"""

import asyncio
from sqlalchemy import text
from app.core.database import engine


async def create_tables():
    async with engine.begin() as conn:
        # Minimal users table
        await conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL,
                last_activity TIMESTAMP,
                preferences JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
        ))

        # Minimal projects table
        await conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id UUID PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                owner_id UUID,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
        ))

        # Minimal project_members table
        await conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS project_members (
                id UUID PRIMARY KEY,
                project_id UUID NOT NULL,
                user_id UUID NOT NULL,
                role VARCHAR(50) NOT NULL,
                joined_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(project_id, user_id)
            );
            """
        ))

        # Minimal activities table
        await conn.execute(text(
            """
            CREATE TABLE IF NOT EXISTS activities (
                id UUID PRIMARY KEY,
                type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                user_id UUID NOT NULL,
                project_id UUID,
                location VARCHAR(500),
                meta_data JSONB DEFAULT '{}',
                priority VARCHAR(20) DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
        ))

        print("Created minimal demo tables (if they were missing)")


def main():
    asyncio.run(create_tables())


if __name__ == '__main__':
    main()
