Demo quickstart — run locally for a hackathon presentation

Goal: get a working demo of the backend + minimal frontend to show streaming presence, activity, and deployment preview features without provisioning cloud infra.

Prereqs
- Docker and docker-compose installed
- Node.js + npm (for frontend) if you want to run the frontend locally

1) Start local services

From the repository root run:

```bash
docker-compose up --build
```

This starts:
- PostgreSQL on 5432
- Redis on 6379
- Backend FastAPI on http://localhost:8000 (with live-reload)

2) Create DB schema (quick options)

This repo uses Alembic for migrations. For a quick demo you can:
- Run migrations if you prefer: `docker-compose exec backend alembic upgrade head`
- Or rely on the app to create minimal tables for demo (the seed script inserts records assuming tables exist). If you haven't run migrations, run them now.

3) Seed demo data

Run the seed script inside the backend container (or locally if your env is configured):

```bash
# inside repo root
docker-compose exec backend python scripts/seed_demo.py
```

You should see a printed confirmation when seeding completes.

4) Open the API and docs

- API root / health: http://localhost:8000/
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

5) Frontend (optional)

Run the frontend dev server from the `frontend/` folder and point its API base URL to `http://localhost:8000/api`.

```bash
cd frontend
npm install
npm run dev
```

6) Demo checklist
- Show the API docs and a sample endpoint (login/register)
- Show presence activity via WebSocket endpoints (connect browser tabs to `/ws/{project_id}`)
- Show seeded user and project data via the API (GET /api/projects, /api/users)
- Trigger a deployment preview flow (if configured) or simulate a deployment by hitting the deployment endpoints

Troubleshooting
- If the backend fails to connect to Postgres, ensure Docker ports are mapped and DB credentials match `.env` or container environment.
- Use `docker-compose logs -f backend` to stream logs.

If you want, I can also:
- Add a simple `docker-compose.override.yml` that runs migrations automatically on `docker-compose up` and runs the seed script after the DB is ready.
- Add a small script to open multiple browser windows and simulate multi-user presence for the demo.
