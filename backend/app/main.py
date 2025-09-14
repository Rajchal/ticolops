"""
Ticolops - Track. Collaborate. Deploy. Succeed.
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.redis import init_redis
from app.core.logging import setup_logging
from app.api.auth import router as auth_router
from app.api.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    setup_logging()
    await init_db()
    await init_redis()
    
    yield
    
    # Shutdown
    # Add cleanup logic here if needed


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Ticolops API",
        description="Real-time collaborative platform for student project management with automated DevOps",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auth_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    
    return app


app = create_app()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "Ticolops API is running", "status": "healthy"}


@app.get("/health")
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "service": "ticolops-api",
        "version": "1.0.0"
    }