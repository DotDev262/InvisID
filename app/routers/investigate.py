import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.image_service import extract_watermark
from app.config import get_settings

router = APIRouter(prefix="/investigate", tags=["investigation"])
settings = get_settings()


@router.post("/")
async def investigate_image(file: UploadFile = File(...)):

    if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=400, detail="Invalid file type")

    temp_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_path = os.path.join(settings.UPLOAD_DIR, temp_filename)

    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    employee_id = extract_watermark(temp_path)

    print("DECODED WATERMARK:", employee_id)

    if not employee_id:
        raise HTTPException(status_code=400, detail="No employee watermark detected")

    return {
        "status": "leak_detected",
        "employee_id": employee_id,
        "message": f"Image leaked by employee {employee_id}"
    }