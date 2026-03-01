from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
import os
import shutil
import uuid
import time
from typing import List

from app.config import get_settings
from app.dependencies.auth import AdminUser
from app.routers import jobs
from app.models.schemas import UploadResponse, InvestigationResponse

router = APIRouter(tags=["admin"])
settings = get_settings()

def process_investigation(job_id: str, file_path: str):
    """Background task to extract watermark."""
    try:
        # Simulate processing time
        time.sleep(5)
        
        # Mock result
        result = {
            "leaked_by": "EMP-001",
            "confidence": 0.98,
            "original_filename": "secret_plan.jpg",
            "extraction_timestamp": time.time()
        }
        
        jobs.update_job(job_id, "completed", result=result)
        
        # Clean up uploaded file for investigation
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        jobs.update_job(job_id, "failed", error=str(e))

@router.post("/admin/upload", response_model=UploadResponse)
async def upload_master_image(
    user: AdminUser,
    file: UploadFile = File(...)
):
    """Upload a master image for leak attribution."""
    # Check file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Generate unique ID and filename
    image_id = str(uuid.uuid4())
    filename = f"{image_id}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save image: {str(e)}")
    finally:
        file.file.close()

    return {
        "id": image_id,
        "filename": filename,
        "status": "uploaded",
        "message": "Master image uploaded successfully"
    }

@router.post("/investigate", response_model=InvestigationResponse)
async def investigate_image(
    user: AdminUser,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Extract watermark from a leaked image."""
    # Check file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Save file for investigation
    job_id = jobs.create_job("investigation")
    file_path = os.path.join(settings.RESULT_DIR, f"{job_id}{ext}")
    
    os.makedirs(settings.RESULT_DIR, exist_ok=True)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    background_tasks.add_task(process_investigation, job_id, file_path)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Investigation started"
    }
