import base64
import os
import uuid
import json
from io import BytesIO

import numpy as np
from fastapi import APIRouter, File, HTTPException, Form
from PIL import Image, ImageFilter
from app.config import get_settings
from app.dependencies.auth import AdminUser
from app.utils.crypto import decrypt_data
from app.utils.logging import get_logger

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()
logger = get_logger("app.stress_test")

@router.post("/stress-test/")
async def perform_stress_test(
    user: AdminUser,
    image_id: str = Form(...),
    target_id: str = Form(...),
    attack_type: str = Form(...), # Comma-separated list of attacks
    intensity: str = Form(...),   # JSON string mapping attack names to their intensity
    ignore_exif: str = Form("false")
):
    """
    Simulates a real-world forensic cycle:
    1. Watermarks a master image with a custom ID.
    2. Applies sequential adversarial attacks.
    3. Attempts to extract the custom ID back.
    """
    ignore_exif_bool = ignore_exif.lower() == "true"
    # 1. Get the master image filename
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
        raise HTTPException(status_code=404, detail=f"Internal asset file missing: {image_id}.png")

    # 2. Decrypt and load
    try:
        with open(path, "rb") as f:
            encrypted_data = f.read()
            decrypted = decrypt_data(encrypted_data)
        
        img_raw = Image.open(BytesIO(decrypted))
        if img_raw.mode not in ("RGB", "L"):
            img_raw = img_raw.convert("RGB")
            
        # --- DYNAMIC FORENSIC CYCLE ---
        from app.services.image_service import embed_watermark, extract_watermark
        
        # A. Apply Watermark First
        buf_wm = BytesIO()
        img_raw.save(buf_wm, format="PNG")
        img_watermarked_arr = embed_watermark(buf_wm.getvalue(), target_id)
        img = Image.fromarray(img_watermarked_arr)
        
    except Exception as e:
        logger.error(f"Forensic prep failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Forensic Preparation Error")

    # 3. Apply Attacks
    intensity_map = json.loads(intensity)
    attacks = attack_type.split(',')
    
    try:
        for attack in attacks:
            attack = attack.strip()
            if not attack: continue
            
            i = float(intensity_map.get(attack, 0.5))
            
            if attack == "compression":
                quality = int(100 - (i * 90)) # Q100 to Q10
                if quality < 10: quality = 10
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=quality)
                buffer.seek(0)
                img = Image.open(buffer).copy()
            elif attack == "blur":
                radius = i * 5 # Up to R5 blur
                img = img.filter(ImageFilter.GaussianBlur(radius=radius))
            elif attack == "noise":
                arr = np.array(img)
                # Matches noise_attack in script
                noise = np.random.normal(0, i * 50, arr.shape).astype(np.float32)
                arr = np.clip(arr.astype(np.float32) + noise, 0, 255).astype(np.uint8)
                img = Image.fromarray(arr)
            elif attack == "rotation":
                angle = (i - 0.5) * 90 # -45 to +45 degrees
                img = img.rotate(angle, expand=True, fillcolor=(15, 23, 42))
            elif attack == "scaling":
                scale = 1.0 - (i * 0.8) # 100% to 20%
                if scale < 0.1: scale = 0.1
                new_size = (int(img.width * scale), int(img.height * scale))
                # Using LANCZOS for higher quality scaling as in script
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                # Resizing back to original to keep detection grid mostly intact but blurred
                img = img.resize((img_raw.width, img_raw.height), Image.Resampling.LANCZOS)
            elif attack == "brightness":
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Brightness(img)
                img = enhancer.enhance(i * 2.0) # 0 to 2.0
            elif attack == "contrast":
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(i * 2.0)
            elif attack == "sharpen":
                img = img.filter(ImageFilter.SHARPEN)
            elif attack == "median":
                # Median filter (3x3 or 5x5 based on intensity)
                size = 3 if i < 0.5 else 5
                arr = np.array(img)
                arr = cv2.medianBlur(arr, size)
                img = Image.fromarray(arr)
            elif attack == "grayscale":
                img = img.convert("L").convert("RGB")
            elif attack == "perspective":
                # Simulate perspective skew (Tilt)
                import cv2
                arr = np.array(img)
                h, w = arr.shape[:2]
                pts1 = np.float32([[0,0], [w,0], [0,h], [w,h]])
                # Tilt strength based on intensity
                off = i * 50
                pts2 = np.float32([[off,off], [w-off*2,off*1.5], [off*1.5,h-off], [w-off,h-off*2]])
                M = cv2.getPerspectiveTransform(pts1, pts2)
                arr = cv2.warpPerspective(arr, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
                img = Image.fromarray(arr)
            elif attack == "whatsapp":
                # Compound attack: Compression + Scaling
                quality = 70
                scale = 0.6
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=quality)
                img = Image.open(buffer).copy()
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                img = img.resize((img_raw.width, img_raw.height), Image.Resampling.LANCZOS)
    except Exception as e:
        logger.error(f"Attack failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Attack simulation failed")

    # 4. Prepare result for UI
    buffered = BytesIO()
    img.save(buffered, format="JPEG")
    attacked_bytes = buffered.getvalue()
    img_str = base64.b64encode(attacked_bytes).decode()
    
    # 5. Extraction with Homography Alignment (extreme resilience)
    extracted_id, confidence = extract_watermark(attacked_bytes, master_data=img_raw, ignore_exif=ignore_exif_bool)
    
    return {
        "attacked_image": f"data:image/jpeg;base64,{img_str}",
        "result": {
            "leaked_by": extracted_id if extracted_id else "NONE DETECTED",
            "confidence": confidence,
            "status": "Success" if extracted_id == target_id else "Identity Lost"
        }
    }
