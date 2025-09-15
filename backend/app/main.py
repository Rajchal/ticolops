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
try:
    # Import socketio app lazily; in some dev containers socketio may not be installed
    # and we want the native /api/ws fallback to work without failure.
    from app.services.socketio_server import socketio_app
except Exception:
    socketio_app = None
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
    
    # Configure CORS (allow all origins locally to make frontend dev easier)
    # For production set `ALLOWED_HOSTS` appropriately and avoid wildcard origins.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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

    # Mount Socket.IO ASGI app at /socket.io when available so socket.io clients
    # (tests or other integrations) receive proper engine.io polling and upgrade
    # responses. If the socketio package is not installed the lazy import above
    # will leave `socketio_app` as None and we fall back to a lightweight
    # placeholder route in DEBUG to reduce 404 noise.
    if socketio_app is not None:
        app.mount('/socket.io', socketio_app)
    elif settings.DEBUG:
        # During DEBUG show a lightweight placeholder response for socket.io polling
        # to reduce 404 noise when frontend clients attempt socket.io in dev.
        from fastapi import APIRouter
        sio_router = APIRouter()

        @sio_router.get('/socket.io/')
        async def socketio_polling_placeholder():
            return {"message": "socket.io placeholder (DEBUG)"}

        app.include_router(sio_router)

        # Also add a WebSocket catcher for socket.io upgrade attempts so the
        # server responds cleanly instead of emitting 403/connection rejected
        # logs when socketio isn't available in DEBUG.
        from fastapi import WebSocket

        @app.websocket('/socket.io/')
        async def _socketio_ws_catcher(websocket: WebSocket):
            # Accept and close immediately to inform clients gracefully.
            await websocket.accept()
            await websocket.close(code=1000)

    # Lightweight ASGI middleware to quietly handle engine.io/socket.io polling
    # requests from clients that attempt socket.io in dev. This prevents a
    # stream of 404/403 logs without changing the main app behavior.
    @app.middleware("http")
    async def _engineio_polling_quiet_middleware(request, call_next):
        try:
            # engine.io polling requests include an `EIO` query param and
            # transport=polling. If present and socketio isn't mounted return
            # an empty 204 to keep logs quiet.
            q = request.query_params
            if ("EIO" in q and q.get("transport") in ("polling", "websocket")):
                from fastapi.responses import Response
                return Response(status_code=204)
        except Exception:
            # Be defensive: if anything goes wrong, continue to the app
            pass

        response = await call_next(request)
        return response
    
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