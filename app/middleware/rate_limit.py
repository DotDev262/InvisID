"""Rate limiting middleware."""

import hashlib
import time

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

settings = get_settings()

# Simple in-memory rate limiter
rate_limit_store: dict[str, list[float]] = {}

def clear_rate_limits():
    """Helper for tests to reset state."""
    global rate_limit_store
    rate_limit_store.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    async def dispatch(self, request: Request, call_next):

        # Skip rate limiting for health check and docs
        if request.url.path in [
            "/health",
            "/",
            "/docs",
            "/openapi.json",
            "/api/docs",
            "/api/openapi.json",
        ]:
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("X-API-Key", "anonymous")
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        now = time.time()
        minute_ago = now - 60

        # Clean old entries
        if key_hash in rate_limit_store:
            rate_limit_store[key_hash] = [
                t for t in rate_limit_store[key_hash] if t > minute_ago
            ]
        else:
            rate_limit_store[key_hash] = []

        # Check limit
        if len(rate_limit_store.get(key_hash, [])) >= settings.RATE_LIMIT_PER_MINUTE:
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {settings.RATE_LIMIT_PER_MINUTE} requests/minute."}
            )

        # Add current request
        rate_limit_store[key_hash].append(now)

        return await call_next(request)