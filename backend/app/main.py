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
from app.api import api_router
from app.services.websocket_pubsub import initialize_websocket_pubsub, shutdown_websocket_pubsub
from app.services.presence_manager import start_presence_manager, stop_presence_manager
from app.services.conflict_detector import start_conflict_detector, stop_conflict_detector


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    setup_logging()
    await init_db()
    await init_redis()
    await initialize_websocket_pubsub()
    await start_presence_manager()
    await start_conflict_detector()
    
    yield
    
    # Shutdown
    await stop_conflict_detector()
    await stop_presence_manager()
    await shutdown_websocket_pubsub()


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
    
    # Include API router
    app.include_router(api_router, prefix="/api")
    
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