import os
import sys
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models.schemas import HealthResponse
from app.routers import admin, images, jobs
from app.utils.logging import get_logger, setup_logging
from app.routers import investigate

# Initialize settings and structured logging
settings = get_settings()
setup_logging(level=settings.LOG_LEVEL)
logger = get_logger("app.main")

app = FastAPI(
    title="InvisID API",
    description="""...""",
    version="1.0.0"
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent stack traces in responses."""
    logger.error(
        f"Global error on {request.url.path}: {str(exc)}", 
        exc_info=True,
        extra={"url": str(request.url), "method": request.method}
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact support."},
    )

# Add security headers
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(admin.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(investigate.router, prefix="/api")

@app.get("/", tags=["system"])
async def root():
    """Welcome endpoint."""
    return {"message": "InvisID API", "status": "running"}

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Enhanced health check with storage status."""
    storage_ok = os.access(settings.UPLOAD_DIR, os.W_OK)
    
    status = "healthy" if storage_ok else "unhealthy"
    
    return {
        "status": status,
        "storage_ok": storage_ok,
        "timestamp": datetime.now(timezone.utc)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
