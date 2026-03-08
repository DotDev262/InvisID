import os
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings
from app.dependencies.auth import EmployeeUser
from app.models.schemas import ImageResponse
from app.utils.logging import get_logger
from app.services.image_service import embed_watermark


router = APIRouter(prefix="/images", tags=["images"])
settings = get_settings()
logger = get_logger("app.images")


@router.get("/", response_model=List[ImageResponse])
async def list_images(user: EmployeeUser):
    """
    List all available master images for the authorized employee.
    """

    upload_dir = settings.UPLOAD_DIR

    if not os.path.exists(upload_dir):
        logger.info(f"Upload directory not found for user: {user.employee_id}")
        return []

    files = os.listdir(upload_dir)
    images = []

    for f in files:
        if any(f.lower().endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):

            image_id = os.path.splitext(f)[0]

            images.append(
                {
                    "id": image_id,
                    "filename": f,
                    "url": f"/api/images/{image_id}/download",
                }
            )

    logger.info(f"Listed {len(images)} images for user {user.employee_id}")

    return images


@router.get("/{image_id}/download")
async def download_image(
    image_id: str,
    user: EmployeeUser,
    background_tasks: BackgroundTasks,
):

    upload_dir = settings.UPLOAD_DIR

    if not os.path.exists(upload_dir):
        raise HTTPException(status_code=404, detail="Upload directory missing")

    files = os.listdir(upload_dir)

    # pick first valid image
    image_file = None
    for f in files:
        if any(f.lower().endswith(ext) for ext in settings.ALLOWED_EXTENSIONS):
            image_file = f
            break

    if image_file is None:
        raise HTTPException(status_code=404, detail="Image not found")

    input_path = os.path.join(upload_dir, image_file)

    base_name = os.path.splitext(image_file)[0]

    output_filename = f"watermarked_{user.employee_id}_{base_name}.png"
    output_path = os.path.join(upload_dir, output_filename)

    if not os.path.exists(output_path):

        logger.info(
            f"Embedding watermark for employee {user.employee_id} on image {image_file}"
        )

        embed_watermark(
            input_path=input_path,
            watermark_data=user.employee_id,
            output_path=output_path,
        )

    return FileResponse(
        output_path,
        media_type="image/png",
        filename=output_filename,
    )