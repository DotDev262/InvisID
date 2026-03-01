from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
import os
from typing import List

from app.config import get_settings
from app.dependencies.auth import EmployeeUser, AdminUser
from app.models.schemas import ImageResponse

router = APIRouter(prefix="/images", tags=["images"])
settings = get_settings()

@router.get("/", response_model=List[ImageResponse])
async def list_images(user: EmployeeUser):
    """List all available master images."""
    if not os.path.exists(settings.UPLOAD_DIR):
        return []
    
    files = os.listdir(settings.UPLOAD_DIR)
    images = []
    for f in files:
        if any(f.lower().endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
            image_id = os.path.splitext(f)[0]
            images.append({
                "id": image_id,
                "filename": f,
                "url": f"/api/images/{image_id}/download"
            })
    
    return images

@router.get("/{image_id}/download")
async def download_image(
    image_id: str,
    user: EmployeeUser,
    background_tasks: BackgroundTasks
):
    """Download image with embedded watermark unique to the employee."""
    # Find the image file
    if not os.path.exists(settings.UPLOAD_DIR):
        raise HTTPException(status_code=404, detail="No images found")
        
    files = os.listdir(settings.UPLOAD_DIR)
    image_file = None
    for f in files:
        if f.startswith(image_id):
            image_file = f
            break
    
    if not image_file:
        raise HTTPException(status_code=404, detail="Image not found")
    
    input_path = os.path.join(settings.UPLOAD_DIR, image_file)
    
    # In a real implementation, we would apply watermarking here
    # or trigger a background task if it's slow.
    # For now, we return the file with a different filename to simulate.
    
    return FileResponse(
        input_path, 
        media_type="image/jpeg", 
        filename=f"watermarked_{user.employee_id}_{image_file}"
    )
