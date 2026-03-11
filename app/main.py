import os
import sys
import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models.schemas import HealthResponse
from app.routers import admin, auth, images, investigate, jobs, logs, stress_test, security
from app.utils.logging import get_logger, setup_logging
from app.utils.instance import SERVER_INSTANCE_ID

# Initialize settings and structured logging
settings = get_settings()
setup_logging(level=settings.LOG_LEVEL)
logger = get_logger("app.main")

async def background_trash_cleanup():
    """
    Background task that runs periodically to permanently delete 
    assets that have been in the trash for more than the retention period.
    """
    while True:
        try:
            logger.info("Running scheduled trash cleanup...")
            from app.utils.db import get_db
            conn = get_db()
            cursor = conn.cursor()
            
            # Find assets to delete (older than settings.TRASH_RETENTION_DAYS)
            cursor.execute("SELECT id, filename FROM master_images WHERE deleted_at IS NOT NULL")
            to_delete = cursor.fetchall()
            
            for asset in to_delete:
                # Check if deletion date is indeed old enough
                d_at = datetime.fromisoformat(asset['deleted_at'])
                if datetime.now(timezone.utc) - d_at > timedelta(days=settings.TRASH_RETENTION_DAYS):
                    image_id = asset['id']
                    filename = asset['filename']
                    ext = os.path.splitext(filename)[1]
                    file_path = os.path.join(settings.UPLOAD_DIR, f"{image_id}{ext}")
                    
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        logger.info(f"Permanently deleted asset from disk: {filename}")
                    
                    cursor.execute("DELETE FROM master_images WHERE id = ?", (image_id,))
                    logger.info(f"Removed asset record from database: {image_id}")
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Trash cleanup task failed: {str(e)}")
        await asyncio.sleep(86400) # Once a day

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start background tasks
    cleanup_task = asyncio.create_task(background_trash_cleanup())
    yield
    # Shutdown: Clean up tasks
    cleanup_task.cancel()

app = FastAPI(
    title="InvisID API",
    description="""
    Leak Attribution System for Sensitive Images.
    
    This API provides tools for:
    * **Administrators**: Uploading master images and investigating leaks.
    * **Employees**: Downloading watermarked images for legitimate use.
    """,
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to prevent stack traces in responses."""
    logger.error(
        f"Global error on {request.url.path}: {str(exc)}",
        exc_info=True,
        extra={"url": str(request.url), "method": request.method},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact support."},
    )


# Add security headers
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting
app.add_middleware(RateLimitMiddleware)

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.middleware("http")
async def add_security_and_instance_headers(request: Request, call_next):
    response = await call_next(request)
    # Add Instance ID for session invalidation on restart
    response.headers["X-Instance-ID"] = SERVER_INSTANCE_ID
    
    # Disable cache for UI and static assets during development
    if request.url.path.startswith("/static") or request.url.path == "/" or "/admin" in request.url.path:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(images.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(investigate.router, prefix="/api")
app.include_router(stress_test.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(security.router, prefix="/api")

# UI Routes
@app.get("/")
async def index():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/gallery")
async def gallery_ui():
    return FileResponse(os.path.join(static_dir, "user/gallery.html"))

@app.get("/admin")
async def admin_dashboard_ui():
    return FileResponse(os.path.join(static_dir, "admin/dashboard.html"))

@app.get("/admin/investigate")
async def admin_investigate_ui():
    return FileResponse(os.path.join(static_dir, "admin/investigation.html"))

@app.get("/admin/trash")
async def admin_trash_ui():
    return FileResponse(os.path.join(static_dir, "admin/trash.html"))

@app.get("/admin/audit-logs")
async def admin_audit_logs_ui():
    return FileResponse(os.path.join(static_dir, "admin/audit_logs.html"))

@app.get("/admin/stress-test")
async def admin_stress_test_ui():
    return FileResponse(os.path.join(static_dir, "admin/stress_test.html"))


@app.get("/robots.txt")
async def serve_robots():
    return FileResponse(os.path.join(static_dir, "robots.txt"))


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """Enhanced health check with storage status."""
    storage_ok = os.access(settings.UPLOAD_DIR, os.W_OK)

    status = "healthy" if storage_ok else "unhealthy"

    return {"status": status, "storage_ok": storage_ok, "timestamp": datetime.now(timezone.utc)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
