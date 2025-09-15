"""
Ticolops - Track. Collaborate. Deploy. Succeed.
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.middleware import SecurityHeadersMiddleware, SimpleRateLimitMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.core.redis import init_redis
from app.core.logging import setup_logging
from app.core.openapi import custom_openapi
from app.api import api_router
from app.api.enhanced_docs import ALL_EXAMPLES, COMMON_RESPONSES
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
        description="""
        ## Ticolops - Track. Collaborate. Deploy. Succeed.
        
        A comprehensive real-time collaborative platform designed for student project management 
        with integrated automated DevOps workflows.
        
        ### Key Features
        
        * **Real-time Collaboration**: Track team member activities and presence in real-time
        * **Conflict Detection**: Automatically detect and resolve collaboration conflicts
        * **Automated DevOps**: Seamless repository integration with automated deployments
        * **Team Management**: Comprehensive project and team member management
        * **Activity Tracking**: Detailed activity logging and analytics
        * **Notification System**: Multi-channel notification delivery
        
        ### Authentication
        
        This API uses JWT (JSON Web Tokens) for authentication. Include the token in the 
        Authorization header as `Bearer <token>`.
        
        ### Rate Limiting
        
        API endpoints are rate-limited to ensure fair usage. Limits vary by endpoint and user role.
        
        ### WebSocket Support
        
        Real-time features are powered by WebSocket connections. Connect to `/ws/{project_id}` 
        for real-time updates.
        """,
        version="1.0.0",
        lifespan=lifespan,
        contact={
            "name": "Ticolops Support",
            "email": "support@ticolops.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.ticolops.com",
                "description": "Production server"
            }
        ]
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Security headers and simple in-process rate limiting (example)
    # For distributed/production environments prefer ingress- or gateway-level rate limiting
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SimpleRateLimitMiddleware, max_requests=120, window_seconds=60)
    
    # Include API router
    app.include_router(api_router, prefix="/api")
    
    # Set custom OpenAPI schema
    app.openapi = lambda: custom_openapi(app)
    
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