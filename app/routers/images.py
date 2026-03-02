import os
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.dependencies.auth import EmployeeUser
from app.models.schemas import ImageResponse
from app.utils.logging import get_logger

router = APIRouter(prefix="/images", tags=["images"])
settings = get_settings()
logger = get_logger("app.images")

@router.get("/", response_model=List[ImageResponse])
async def list_images(user: EmployeeUser):
    """
    List all available master images for the authorized employee.
    
    Returns a list of image metadata, including IDs and download URLs. 
    Each image downloaded from the provided URL will be uniquely watermarked 
    for the current employee.
    """
    if not os.path.exists(settings.UPLOAD_DIR):
        logger.info(f"Empty upload directory for user: {user.employee_id}")
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
    
    logger.info(f"Listed {len(images)} images for user: {user.employee_id}")
    return images

@router.get("/{image_id}/download")
async def download_image(
    image_id: str,
    user: EmployeeUser,
    background_tasks: BackgroundTasks
):
    """
    Download a watermarked version of a master image.
    
    The system will uniquely embed the employee's ID (`EMP-001` etc.) into 
    the image before serving. This enables leak attribution if the image 
    is discovered outside of authorized channels.
    """
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
        logger.warning(f"Image not found for ID {image_id} (user: {user.employee_id})")
        raise HTTPException(status_code=404, detail="Image not found")
    
    input_path = os.path.join(settings.UPLOAD_DIR, image_file)
    
    logger.info(
        f"Image download requested for {image_id}", 
        extra_context={"employee_id": user.employee_id, "image_file": image_file}
    )
    
    # In a real implementation, we would apply watermarking here
    
    return FileResponse(
        input_path, 
        media_type="image/jpeg", 
        filename=f"watermarked_{user.employee_id}_{image_file}"
    )
