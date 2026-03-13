import base64
import os
import uuid
import json
from io import BytesIO

import numpy as np
import cv2
from fastapi import APIRouter, File, HTTPException, Form
from PIL import Image, ImageFilter, ImageEnhance
from app.config import get_settings
from app.dependencies.auth import AdminUser
from app.utils.crypto import decrypt_data
from app.utils.logging import get_logger
from app.services.image_service import embed_watermark, extract_watermark

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()
logger = get_logger("app.stress_test")

@router.post("/stress-test/")
async def perform_stress_test(
    user: AdminUser,
    image_id: str = Form(...),
    target_id: str = Form(...),
    attack_type: str = Form(...), 
    intensity: str = Form(...),   
    ignore_exif: str = Form("false")
):
    """
    Stress-Test Lab: Synchronized with Platinum Suite Forensic Audit.
    Simulates high-noise and geometric distribution attacks.
    """
    ignore_exif_bool = ignore_exif.lower() == "true"
    
    # 1. Load Master Asset
    from app.utils.db import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT filename FROM master_images WHERE id = ?", (image_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Master image not found")
        
    path = os.path.join(settings.UPLOAD_DIR, f"{image_id}.png")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Internal file missing")

    try:
        with open(path, "rb") as f:
            decrypted = decrypt_data(f.read())
        
        # Load as OpenCV BGR for high-precision attacks
        nparr = np.frombuffer(decrypted, np.uint8)
        img_master = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 2. Apply Invisible Watermark
        # We use the raw array directly for peak precision
        watermarked = embed_watermark(img_master, target_id)
        current_img = watermarked.copy()
        
    except Exception as e:
        logger.error(f"Stress test prep failed: {e}")
        raise HTTPException(status_code=500, detail="Preparation Error")

    # 3. Apply Platinum Suite Attacks (Synchronized with forensic_ultimate_test.py)
    intensity_map = json.loads(intensity)
    attack_list = [a.strip() for a in attack_type.split(',') if a.strip()]
    
    try:
        for a_type in attack_list:
            i = float(intensity_map.get(a_type, 0.5))
            
            if a_type == "compression":
                quality = int(100 - (i * 90)) # Q100 to Q10
                buf = BytesIO()
                pil_tmp = Image.fromarray(cv2.cvtColor(current_img, cv2.COLOR_BGR2RGB))
                pil_tmp.save(buf, format="JPEG", quality=max(10, quality))
                current_img = cv2.cvtColor(np.array(Image.open(BytesIO(buf.getvalue()))), cv2.COLOR_RGB2BGR)
                
            elif a_type == "blur":
                radius = i * 5
                pil_tmp = Image.fromarray(cv2.cvtColor(current_img, cv2.COLOR_BGR2RGB))
                pil_tmp = pil_tmp.filter(ImageFilter.GaussianBlur(radius=radius))
                current_img = cv2.cvtColor(np.array(pil_tmp), cv2.COLOR_RGB2BGR)
                
            elif a_type == "noise":
                noise = np.random.normal(0, i * 50, current_img.shape).astype(np.float32)
                current_img = np.clip(current_img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
                
            elif a_type == "rotation":
                angle = (i - 0.5) * 90 # -45 to +45
                h, w = current_img.shape[:2]
                M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
                current_img = cv2.warpAffine(current_img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
                
            elif a_type == "scaling":
                scale = 1.0 - (i * 0.8) # 100% to 20%
                h, w = current_img.shape[:2]
                new_size = (int(w * scale), int(h * scale))
                resized = cv2.resize(current_img, new_size, interpolation=cv2.INTER_LANCZOS4)
                current_img = cv2.resize(resized, (w, h), interpolation=cv2.INTER_LANCZOS4)
                
            elif a_type == "brightness":
                pil_tmp = Image.fromarray(cv2.cvtColor(current_img, cv2.COLOR_BGR2RGB))
                current_img = cv2.cvtColor(np.array(ImageEnhance.Brightness(pil_tmp).enhance(i * 2.0)), cv2.COLOR_RGB2BGR)
                
            elif a_type == "contrast":
                pil_tmp = Image.fromarray(cv2.cvtColor(current_img, cv2.COLOR_BGR2RGB))
                current_img = cv2.cvtColor(np.array(ImageEnhance.Contrast(pil_tmp).enhance(i * 2.0)), cv2.COLOR_RGB2BGR)
                
            elif a_type == "sharpen":
                pil_tmp = Image.fromarray(cv2.cvtColor(current_img, cv2.COLOR_BGR2RGB))
                current_img = cv2.cvtColor(np.array(pil_tmp.filter(ImageFilter.SHARPEN)), cv2.COLOR_RGB2BGR)
                
            elif a_type == "median":
                size = 3 if i < 0.5 else 5
                current_img = cv2.medianBlur(current_img, size)
                
            elif a_type == "grayscale":
                current_img = cv2.cvtColor(cv2.cvtColor(current_img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
                
            elif a_type == "perspective":
                h, w = current_img.shape[:2]
                pts1 = np.float32([[0,0], [w,0], [0,h], [w,h]])
                off = i * 60 # Shift up to 60px
                pts2 = np.float32([[off,off], [w-off,off*1.2], [off*0.8,h-off], [w-off*1.1,h-off]])
                M = cv2.getPerspectiveTransform(pts1, pts2)
                current_img = cv2.warpPerspective(current_img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
                
            elif a_type == "whatsapp":
                # Comp + Scale combo
                buf = BytesIO()
                pil_tmp = Image.fromarray(cv2.cvtColor(current_img, cv2.COLOR_BGR2RGB))
                pil_tmp.save(buf, format="JPEG", quality=70)
                current_img = cv2.cvtColor(np.array(Image.open(BytesIO(buf.getvalue()))), cv2.COLOR_RGB2BGR)
                h, w = current_img.shape[:2]
                resized = cv2.resize(current_img, (int(w*0.6), int(h*0.6)), interpolation=cv2.INTER_LANCZOS4)
                current_img = cv2.resize(resized, (w, h), interpolation=cv2.INTER_LANCZOS4)

    except Exception as e:
        logger.error(f"Attack execution failed: {e}")
        raise HTTPException(status_code=500, detail="Simulation Error")

    # 4. Forensic Extraction (The Proof)
    extracted_id, conf, aligned_img = extract_watermark(current_img, master_data=img_master, ignore_exif=ignore_exif_bool)
    
    # Use the aligned image for the result preview (Forensic Evidence style)
    display_img = aligned_img if aligned_img is not None else current_img
    _, encoded = cv2.imencode(".jpg", display_img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    img_str = base64.b64encode(encoded).decode()

    return {
        "attacked_image": f"data:image/jpeg;base64,{img_str}",
        "result": {
            "leaked_by": extracted_id if extracted_id else "IDENTITY LOST",
            "confidence": conf,
            "status": "Success" if extracted_id == target_id else "Forensic Failure"
        }
    }
