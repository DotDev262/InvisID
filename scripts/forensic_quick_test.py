import cv2
import numpy as np
import io
import os
import sys
import random
import time
from PIL import Image, ImageFilter, ImageEnhance

sys.path.insert(0, '/home/aryan/Code/Projects/InvisID')
from app.services.image_service import embed_watermark, extract_watermark

MAX_SIZE = 1024

def resize_if_needed(img):
    h, w = img.shape[:2]
    if max(h, w) > MAX_SIZE:
        scale = MAX_SIZE / max(h, w)
        return cv2.resize(img, (int(w * scale), int(h * scale)))
    return img

def jpeg_attack(img, q):
    buf = io.BytesIO()
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil_img.save(buf, format="JPEG", quality=q)
    return cv2.cvtColor(np.array(Image.open(io.BytesIO(buf.getvalue()))), cv2.COLOR_RGB2BGR)

def blur_attack(img, r):
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    return cv2.cvtColor(np.array(pil_img.filter(ImageFilter.GaussianBlur(radius=r))), cv2.COLOR_RGB2BGR)

def noise_attack(img, intensity):
    noise = np.random.normal(0, intensity, img.shape).astype(np.float32)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

def rotate_attack(img, angle):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

def quick_audit():
    print("🚀 --- InvisID Quick Forensic Audit --- 🚀")
    start_time = time.time()
    
    from dotenv import load_dotenv
    load_dotenv()
    from app.config import get_settings
    s = get_settings()
    
    upload_dir = s.UPLOAD_DIR
    files = [f for f in os.listdir(upload_dir) if f.endswith('.png') and not f.startswith('test_wm_')]
    if not files:
        return print("❌ No assets found.")

    id_pool = ["EMP-001", "EMP-002", "EMP-003", "CON-004", "INT-005", "GST-006", "EMP-007", "EMP-008", "EMP-999", "ADMIN"]
    
    from app.utils.crypto import decrypt_data
    
    attacks = [
        ("Baseline", lambda x: x),
        ("JPEG Q50", lambda x: jpeg_attack(x, 50)),
        ("Blur R2", lambda x: blur_attack(x, 2)),
        ("Noise S&P", lambda x: noise_attack(x, 15)),
        ("Rotation 15°", lambda x: rotate_attack(x, 15)),
    ]
    
    total_passed = 0
    total_tests = 0
    
    for chosen_file in files:
        target_id = random.choice(id_pool)
        
        try:
            with open(os.path.join(upload_dir, chosen_file), "rb") as f:
                decrypted = decrypt_data(f.read())
            img_master = cv2.imdecode(np.frombuffer(decrypted, np.uint8), cv2.IMREAD_COLOR)
            img_master = resize_if_needed(img_master)
            
            watermarked = embed_watermark(img_master, target_id)
            
            print(f"\n🔍 {chosen_file[:20]}... | ID: {target_id}")
            print("-" * 40)
            
            for name, attack_func in attacks:
                attacked = attack_func(watermarked)
                ext_id, conf, _ = extract_watermark(attacked, master_data=img_master, ignore_exif=True)
                
                is_pass = ext_id == target_id
                if is_pass:
                    total_passed += 1
                total_tests += 1
                
                status = "✅" if is_pass else f"❌ ({ext_id})"
                print(f"  {name:15} -> {status} ({conf*100:.0f}%)")
                
        except Exception as e:
            print(f"💥 Error: {e}")
    
    print("\n" + "=" * 50)
    accuracy = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"🏆 ACCURACY: {accuracy:.1f}% ({total_passed}/{total_tests})")
    print(f"⏱️  Time: {time.time() - start_time:.1f}s")
    print("=" * 50)

if __name__ == "__main__":
    quick_audit()
