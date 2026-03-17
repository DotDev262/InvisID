import cv2
import numpy as np
import io
import os
import random
import time
from multiprocessing import Pool, cpu_count
from PIL import Image, ImageFilter, ImageEnhance
from app.services.image_service import embed_watermark, extract_watermark

# Attack Helpers (Must be top-level for multiprocessing)
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

def brightness_attack(img, factor):
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    return cv2.cvtColor(np.array(ImageEnhance.Brightness(pil_img).enhance(factor)), cv2.COLOR_RGB2BGR)

def scale_attack(img, scale):
    h, w = img.shape[:2]
    # Use INTER_AREA for downscaling like repro_failure.py
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

def whatsapp_attack(img):
    # Synchronized with repro_failure.py (50% + Q50)
    scaled = scale_attack(img, 0.5)
    return jpeg_attack(scaled, 50)

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

def audit_single_asset(args):
    """Worker function to audit a single image asset against all attacks."""
    chosen_file, upload_dir, id_pool = args
    from app.utils.crypto import decrypt_data
    
    target_id = random.choice(id_pool)
    asset_results = []
    
    try:
        # Load and decrypt master
        with open(os.path.join(upload_dir, chosen_file), "rb") as f:
            decrypted = decrypt_data(f.read())
        nparr = np.frombuffer(decrypted, np.uint8)
        img_master = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Embed watermark
        temp_wm_path = os.path.join(upload_dir, f"test_wm_{chosen_file}")
        embed_watermark(img_master, target_id, output_path=temp_wm_path)
        watermarked = cv2.imread(temp_wm_path)
        
        attacks = [
            ("EXIF Recovery", "exif"),
            ("Baseline", lambda x: x),
            ("JPEG (Q50)", lambda x: jpeg_attack(x, 50)),
            ("Gaussian Blur (R2)", lambda x: blur_attack(x, 2)),
            ("Noise (S&P)", lambda x: noise_attack(x, 15)),
            ("Rotation (15°)", lambda x: rotate_attack(x, 15)),
            ("Scaling (50%)", lambda x: scale_attack(x, 0.5)),
            ("WhatsApp (50% + Q50)", lambda x: whatsapp_attack(x)),
            ("Median Filter", lambda x: cv2.medianBlur(x, 3)),
            ("Grayscale", lambda x: cv2.cvtColor(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)),
            ("Perspective", lambda x: perspective_attack(x)),
            ("Sharpen", lambda x: cv2.cvtColor(np.array(Image.fromarray(cv2.cvtColor(x, cv2.COLOR_BGR2RGB)).filter(ImageFilter.SHARPEN)), cv2.COLOR_RGB2BGR)),
            ("Brightness", lambda x: brightness_attack(x, 0.3)),
            ("ULTIMATE COMBO", lambda x: perspective_attack(noise_attack(blur_attack(whatsapp_attack(x), 1), 10)))
        ]
        
        passed = 0
        output_buffer = [f"\n🔍 Asset: {chosen_file} | ID: {target_id}", "-"*50]
        
        for name, attack_func in attacks:
            if name == "EXIF Recovery":
                ext_id, conf, _ = extract_watermark(temp_wm_path, master_data=img_master)
            else:
                attacked = attack_func(watermarked)
                ext_id, conf, _ = extract_watermark(attacked, master_data=img_master, ignore_exif=True)
            
            is_pass = ext_id == target_id
            if is_pass: passed += 1
            status = "✅ PASS" if is_pass else f"❌ FAIL (Got: {ext_id})"
            output_buffer.append(f"  [{name:20}] -> {status} ({conf*100:.0f}%)")
            
        # Cleanup
        if os.path.exists(temp_wm_path): os.remove(temp_wm_path)
        if os.path.exists(temp_wm_path + ".exif"): os.remove(temp_wm_path + ".exif")
        
        score = passed / len(attacks)
        output_buffer.append(f"--- Score: {passed}/{len(attacks)} ---")
        return score, "\n".join(output_buffer)
        
    except Exception as e:
        return 0.0, f"💥 CRASH on {chosen_file}: {e}"

def run_exhaustive_audit():
    print("🚀 --- InvisID Parallel Randomized Forensic Audit --- 🚀")
    start_time = time.time()
    
    from dotenv import load_dotenv
    load_dotenv()
    from app.config import get_settings
    s = get_settings()
    
    upload_dir = s.UPLOAD_DIR
    files = [f for f in os.listdir(upload_dir) if f.endswith('.png') and not f.startswith('test_wm_')]
    if not files: return print("❌ No assets found.")

    id_pool = ["EMP-001", "EMP-002", "EMP-003", "CON-004", "INT-005", "GST-006", "EMP-007", "EMP-008", "EMP-999", "ADMIN"]
    
    # Run in Parallel
    worker_args = [(f, upload_dir, id_pool) for f in files]
    # Use 1 worker per asset, up to the number of available cores
    with Pool(processes=min(len(files), cpu_count())) as pool:
        results = pool.map(audit_single_asset, worker_args)

    # Print consolidated results
    total_score = 0
    for score, log in results:
        print(log)
        total_score += score
        
    print("\n" + "="*50)
    final_avg = (total_score / len(files)) * 100
    print(f"🏆 FINAL PARALLEL SCORE: {final_avg:.1f}% ACCURACY")
    print(f"⏱️  Total Time: {time.time() - start_time:.2f}s")
    print("="*50)

if __name__ == "__main__":
    run_exhaustive_audit()
