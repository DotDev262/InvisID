import os
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from fastapi.responses import FileResponse

from app.config import get_settings
from app.dependencies.auth import EmployeeUser, User, get_current_user

from app.models.schemas import ImageResponse
from app.routers import logs
from app.services.image_service import embed_watermark
from app.utils.logging import get_logger

router = APIRouter(prefix="/images", tags=["images"])
settings = get_settings()
logger = get_logger("app.images")


@router.get("/", response_model=List[ImageResponse])
async def list_images(user: User = Depends(get_current_user)):
    """
    List all available master images for the authorized user.
    """
    from app.utils.db import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename FROM master_images WHERE deleted_at IS NULL")
    rows = cursor.fetchall()
    conn.close()

    images = []
    for row in rows:
        images.append(
            {
                "id": row['id'],
                "filename": row['filename'],
                "url": f"/api/images/{row['id']}/download",
            }
        )

    logger.info(f"Listed {len(images)} images for user {user.role}")
    return images


@router.get("/{image_id}/preview")
async def get_image_preview(
    image_id: str,
    user: User = Depends(get_current_user)
):
    """Serve a preview of the decrypted master image."""
    from app.utils.db import get_db
    from app.utils.crypto import decrypt_data
    
    conn = get_db()
    cursor = conn.cursor()
    # Allow admin to preview trashed images, but employees only non-trashed
    if user.role == "admin":
        cursor.execute("SELECT filename FROM master_images WHERE id = ?", (image_id,))
    else:
        cursor.execute("SELECT filename FROM master_images WHERE id = ? AND deleted_at IS NULL", (image_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Image not found")

    # Internal files are always PNG for forensic integrity
    path = os.path.join(settings.UPLOAD_DIR, f"{image_id}.png")
    
    try:
        with open(path, "rb") as f:
            encrypted_data = f.read()
            decrypted = decrypt_data(encrypted_data)
        
        # Always serve preview as PNG since internal is PNG
        return Response(content=decrypted, media_type="image/png")
    except Exception as e:
        logger.error(f"Failed to serve preview for {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Error loading preview")


@router.get("/{image_id}/download")
async def download_image(
    image_id: str,
    user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Download and watermarked image with forensic tracking."""
    from app.utils.db import get_db
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM master_images WHERE id = ? AND deleted_at IS NULL", (image_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Image not found or in trash")

    image_file = row['filename']
    upload_dir = settings.UPLOAD_DIR
    
    # Master is internally PNG
    input_path = os.path.join(upload_dir, f"{image_id}.png")
    user_id = user.employee_id if user.role == "employee" else user.role

    # Output remains in original filename but we ensure markers are preserved
    output_filename = f"watermarked_{user_id}_{image_file}"
    output_path = os.path.join(upload_dir, output_filename)

    if not os.path.exists(output_path):
        logger.info(
            f"Embedding watermark for {user.role} {user_id} on image {image_file}"
        )
        try:
            from app.utils.crypto import decrypt_data
            with open(input_path, "rb") as f:
                encrypted_data = f.read()
                decrypted_image_bytes = decrypt_data(encrypted_data)

            # Watermark embedding
            embed_watermark(
                input_data=decrypted_image_bytes,
                watermark_data=user_id,
                output_path=output_path,
            )
        except Exception as e:
            logger.error(f"Watermarking failed for {image_file}: {str(e)}")
            raise HTTPException(status_code=500, detail="Watermarking process failed") from e

    # Log the access
    logs.record_log(user_id, "IMAGE_DOWNLOAD", image_file, "success")

    # Serve the file using its original name
    return FileResponse(
        output_path,
        media_type="image/png",
        filename=image_file,
    )
