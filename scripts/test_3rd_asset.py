import cv2
import numpy as np
import io
import os
from PIL import Image, ImageFilter, ImageEnhance
from app.services.image_service import embed_watermark, extract_watermark

def run_asset_test():
    print("🚀 --- Testing Asset: d357fa33-14a7-4740-a8a3-15990c0113b8.png --- 🚀")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    from app.config import get_settings
    s = get_settings()
    
    upload_dir = s.UPLOAD_DIR
    chosen_file = "d357fa33-14a7-4740-a8a3-15990c0113b8.png"
    
    from app.utils.crypto import decrypt_data
    with open(os.path.join(upload_dir, chosen_file), "rb") as f:
        raw_data = f.read()
        decrypted = decrypt_data(raw_data)
    
    nparr = np.frombuffer(decrypted, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    target_id = "EMP-999"
    watermarked = embed_watermark(img, target_id)
    
    # Just run Baseline and JPEG to see if it works
    attacks = [
        ("Baseline", lambda x: x),
        ("JPEG (Q60)", lambda x: jpeg_attack(x, 60)),
        ("Rotation (15°)", lambda x: rotate_attack(x, 15)),
        ("Perspective Skew (Tilt)", lambda x: perspective_attack(x)),
    ]
    
    for name, attack_func in attacks:
        print(f"\n[*] Running Attack: {name}")
        attacked = attack_func(watermarked)
        print(f"[*] Extracting...")
        extracted_id, conf = extract_watermark(attacked, master_data=img)
        status = "✅ PASS" if extracted_id == target_id else "❌ FAIL"
        print(f"  [{name}] -> '{extracted_id}' ({conf*100:.0f}%) | {status}")

# Attack Helpers
def jpeg_attack(img, q):
    buf = io.BytesIO()
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil_img.save(buf, format="JPEG", quality=q)
    buf.seek(0)
    return cv2.cvtColor(np.array(Image.open(buf)), cv2.COLOR_RGB2BGR)

def rotate_attack(img, angle):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

def perspective_attack(img):
    h, w = img.shape[:2]
    pts1 = np.float32([[0,0], [w,0], [0,h], [w,h]])
    pts2 = np.float32([[10,10], [w-20,15], [15,h-10], [w-10,h-20]])
    M = cv2.getPerspectiveTransform(pts1, pts2)
    return cv2.warpPerspective(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

if __name__ == "__main__":
    run_asset_test()
