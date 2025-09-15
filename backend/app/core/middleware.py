from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable
import time


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Simple middleware to add common security headers to all responses."""

    async def dispatch(self, request: Request, call_next: Callable):
        response: Response = await call_next(request)
        headers = {
            "Content-Security-Policy": "default-src 'self'; connect-src 'self' wss: https:; img-src 'self' data:; script-src 'self' 'unsafe-inline';",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        }
        for k, v in headers.items():
            # don't overwrite existing headers
            if k not in response.headers:
                response.headers[k] = v
        return response


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory, per-IP rate limiter (token-bucket sliding window).

    Note: This is a simple implementation intended for small deployments or as a
    middleware example. For production use behind multiple replicas, perform rate
    limiting at the ingress/API gateway (NGINX, Cloud Load Balancer, Kong, or managed API Gateway)
    or use a distributed store (Redis) for counters.
    """

    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = int(max_requests)
        self.window = int(window_seconds)
        self._clients = {}  # ip -> list[timestamps]

    async def dispatch(self, request: Request, call_next: Callable):
        client_ip = "unknown"
        if request.client and request.client.host:
            client_ip = request.client.host
        now = time.time()
        timestamps = self._clients.get(client_ip, [])
        # keep only timestamps within the window
        recent = [t for t in timestamps if now - t < self.window]
        if len(recent) >= self.max_requests:
            return Response(content="Too Many Requests", status_code=429)
        recent.append(now)
        self._clients[client_ip] = recent
        response = await call_next(request)
        return response
