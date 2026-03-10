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
                quality = int(100 - (i * 98))
                buffer = BytesIO()
                img.save(buffer, format="JPEG", quality=quality)
                buffer.seek(0)
                img = Image.open(buffer).copy()
            elif attack == "blur":
                radius = i * 10
                img = img.filter(ImageFilter.GaussianBlur(radius=radius))
            elif attack == "noise":
                arr = np.array(img)
                noise = np.random.normal(0, i * 100, arr.shape).astype(np.int16)
                arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
                img = Image.fromarray(arr)
            elif attack == "rotation":
                angle = i * 180
                img = img.rotate(angle, expand=True, fillcolor=(15, 23, 42))
            elif attack == "scaling":
                scale = 1.0 - (i * 0.9)
                if scale < 0.05: scale = 0.05
                new_size = (int(img.width * scale), int(img.height * scale))
                img = img.resize(new_size, Image.Resampling.NEAREST)
            elif attack == "brightness":
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Brightness(img)
                factor = 1.0 + (i - 0.5) * 4.0 if i > 0.5 else i * 2.0
                img = enhancer.enhance(factor)
            elif attack == "contrast":
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(img)
                factor = 1.0 + (i * 3.0) - 1.5
                img = enhancer.enhance(factor)
            elif attack == "sharpen":
                img = img.filter(ImageFilter.SHARPEN)
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
