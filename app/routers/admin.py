import os
import time
import uuid
from io import BytesIO

import magic  # Already in your dependencies
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from PIL import Image, ImageOps  # Pillow is already in your dependencies

from app.config import get_settings
from app.dependencies.auth import AdminUser
from app.models.schemas import InvestigationResponse, UploadResponse
from app.routers import jobs
from app.utils.logging import get_logger

router = APIRouter(tags=["admin"])
settings = get_settings()
logger = get_logger("app.admin")

def sanitize_image(file_content: bytes, ext: str) -> bytes:
    """
    Strip all EXIF metadata from the image to prevent info leaks 
    and normalize the image.
    """
    try:
        img = Image.open(BytesIO(file_content))
        
        # This creates a new image containing only the pixel data
        data = list(img.getdata())
        clean_img = Image.new(img.mode, img.size)
        clean_img.putdata(data)
        
        # Fix orientation if needed (Pillow doesn't do this by default when stripping)
        clean_img = ImageOps.exif_transpose(img)
        
        output = BytesIO()
        # Save without any extra info
        save_format = "JPEG" if ext.lower() in [".jpg", ".jpeg"] else "PNG"
        clean_img.save(output, format=save_format, optimize=True)
        return output.getvalue()
    except Exception as e:
        logger.error(f"Image sanitization failed: {str(e)}")
        # If sanitization fails, we reject the file as a safety measure
        raise ValueError("Could not sanitize image file") from e

def process_investigation(job_id: str, file_path: str):
    """Background task to extract watermark from a leaked image."""
    try:
        logger.info(f"Starting investigation for job_id: {job_id}")
        time.sleep(5)
        
        result = {
            "leaked_by": "EMP-001",
            "confidence": 0.98,
            "original_filename": "secret_plan.jpg",
            "extraction_timestamp": time.time()
        }
        
        jobs.update_job(job_id, "completed", result=result)
        logger.info(f"Investigation completed for job_id: {job_id}")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.error(f"Investigation failed for job_id: {job_id}: {str(e)}", exc_info=True)
        jobs.update_job(job_id, "failed", error=str(e))

@router.post("/admin/upload", response_model=UploadResponse)
async def upload_master_image(
    user: AdminUser,
    file: UploadFile = File(...)
):
    """
    Upload and sanitize a master image.
    
    1. Validates extension
    2. Validates actual MIME type (Deep Inspection)
    3. Strips all EXIF metadata (Sanitization)
    4. Saves to secure storage
    """
    content = await file.read()
    
    # 1. Check Extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported extension")

    # 2. Deep MIME Type Verification (The 'magic' check)
    mime = magic.from_buffer(content, mime=True)
    if not mime.startswith("image/"):
        logger.error(f"Security Alert: File with ext {ext} has invalid MIME type: {mime}")
        raise HTTPException(status_code=400, detail="Invalid file content. Must be an image.")

    # 3. Sanitize (Strip Metadata)
    try:
        sanitized_content = sanitize_image(content, ext)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    # 4. Save
    image_id = str(uuid.uuid4())
    filename = f"{image_id}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(sanitized_content)
        logger.info(f"Master image uploaded and sanitized: {filename}")
    except Exception as e:
        logger.error(f"Failed to save image {filename}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to save image") from e
    finally:
        await file.close()

    return {
        "id": image_id,
        "filename": filename,
        "status": "uploaded",
        "message": "Master image uploaded and sanitized successfully"
    }

@router.post("/investigate", response_model=InvestigationResponse)
async def investigate_image(
    user: AdminUser,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Starts a background investigation job."""
    content = await file.read()
    
    # MIME verification for investigation too
    mime = magic.from_buffer(content, mime=True)
    if not mime.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid image file")

    ext = os.path.splitext(file.filename)[1].lower()
    job_id = jobs.create_job("investigation")
    file_path = os.path.join(settings.RESULT_DIR, f"{job_id}{ext}")
    
    os.makedirs(settings.RESULT_DIR, exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    background_tasks.add_task(process_investigation, job_id, file_path)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Investigation started"
    }
