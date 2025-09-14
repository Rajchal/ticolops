# Ticolops - Track. Collaborate. Deploy. Succeed.

A real-time collaborative platform for student project management with automated DevOps integration.

## Features

- **Real-time Collaboration**: See where your teammates are working in real-time
- **Automated DevOps**: Connect repositories and get automatic deployments
- **Live Previews**: Share and access live previews of your work
- **Team Management**: Create and manage student project teams
- **Smart Notifications**: Get notified about important team activities
- **Conflict Detection**: Avoid merge conflicts with intelligent collaboration hints

## Technology Stack

### Backend
- **FastAPI** with Python 3.11+ for high-performance async API
- **PostgreSQL** for persistent data storage
- **Redis** for caching and pub/sub messaging
- **SQLAlchemy** with async support for ORM
- **WebSockets** for real-time communication

### Frontend
- **React.js** with TypeScript
- **Tailwind CSS** for styling
- **Socket.io** for real-time features

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- PostgreSQL 15+
- Redis 7+

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ticolops
   ```

2. **Start services with Docker Compose**
   ```bash
   docker-compose up -d postgres redis
   ```

3. **Set up the backend**
   ```bash
   cd backend
   cp .env.example .env
   pip install -r requirements.txt
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start the backend server**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Run tests**
   ```bash
   pytest
   ```

### API Documentation

Once the server is running, visit:
- **Interactive API docs**: http://localhost:8000/docs
- **ReDoc documentation**: http://localhost:8000/redoc

## Project Structure

```
ticolops/
├── backend/
│   ├── app/
│   │   ├── api/          # API routes
│   │   ├── core/         # Core configuration
│   │   ├── models/       # Database models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── websocket/    # WebSocket handlers
│   ├── tests/            # Test files
│   ├── alembic/          # Database migrations
│   └── requirements.txt  # Python dependencies
├── frontend/             # React application (coming soon)
└── docker-compose.yml    # Development services
```

## Development

### Running Tests
```bash
cd backend
pytest
```

### Database Migrations
```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Code Quality
```bash
# Format code
black app/ tests/

# Lint code
flake8 app/ tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.# ticolops
