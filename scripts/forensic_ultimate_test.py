import cv2
import numpy as np
import io
import os
from PIL import Image, ImageFilter, ImageEnhance
from app.services.image_service import embed_watermark, extract_watermark

def run_exhaustive_audit():
    print("🚀 --- InvisID EXHAUSTIVE Forensic Resilience Audit (Platinum Suite) --- 🚀")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    from app.config import get_settings
    s = get_settings()
    
    upload_dir = s.UPLOAD_DIR
    files = [f for f in os.listdir(upload_dir) if f.endswith('.png')]
    
    if not files:
        print("❌ ERROR: No master images found.")
        return

    print(f"📂 Found {len(files)} assets. Starting full-suite audit...\n")
    overall_results = []

    for chosen_file in files:
        print(f"\n🔍 Testing Asset: {chosen_file}")
        print("-" * 40)
        
        from app.utils.crypto import decrypt_data
        with open(os.path.join(upload_dir, chosen_file), "rb") as f:
            raw_data = f.read()
            decrypted = decrypt_data(raw_data)
        
        nparr = np.frombuffer(decrypted, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        target_id = "EMP-999"
        watermarked = embed_watermark(img, target_id)
        
        attacks = [
            ("Baseline", lambda x: x),
            ("JPEG (Q60)", lambda x: jpeg_attack(x, 60)),
            ("Gaussian Blur (R2)", lambda x: blur_attack(x, 2)),
            ("Noise (S&P)", lambda x: noise_attack(x, 15)),
            ("Rotation (15°)", lambda x: rotate_attack(x, 15)),
            ("Scaling (75%)", lambda x: scale_attack(x, 0.75)),
            ("WhatsApp (Comp+Scale)", lambda x: scale_attack(jpeg_attack(x, 70), 0.6)),
            # --- NEW ELITE ATTACKS ---
            ("Median Filter (3x3)", lambda x: cv2.medianBlur(x, 3)),
            ("Grayscale Conversion", lambda x: cv2.cvtColor(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)),
            ("Perspective Skew (Tilt)", lambda x: perspective_attack(x)),
            ("Aggressive Sharpen", lambda x: sharpen_attack(x)),
            ("Brightness (-70%)", lambda x: brightness_attack(x, 0.3)),
            ("ULTIMATE COMBO: Blur+Noise+Comp+Tilt", lambda x: perspective_attack(noise_attack(blur_attack(jpeg_attack(x, 80), 1), 10)))
        ]
        
        asset_passed = 0
        for name, attack_func in attacks:
            try:
                attacked = attack_func(watermarked)
                extracted_id, conf = extract_watermark(attacked, master_data=img)
                
                status = "✅ PASS" if extracted_id == target_id else "❌ FAIL"
                if extracted_id == target_id: asset_passed += 1
                
                print(f"  [{name}] -> '{extracted_id}' ({conf*100:.0f}%) | {status}")
            except Exception as e:
                print(f"  [{name}] -> 💥 CRASH: {e}")
        
        overall_results.append(asset_passed / len(attacks))
        print(f"--- Asset Score: {asset_passed}/{len(attacks)} ---")

    print("\n" + "="*50)
    final_avg = (sum(overall_results) / len(overall_results)) * 100
    print(f"🏆 FINAL EXHAUSTIVE SCORE: {final_avg:.1f}% ACCURACY")
    print("="*50)

# Attack Helpers
def jpeg_attack(img, q):
    buf = io.BytesIO()
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil_img.save(buf, format="JPEG", quality=q)
    buf.seek(0)
    return cv2.cvtColor(np.array(Image.open(buf)), cv2.COLOR_RGB2BGR)

def blur_attack(img, r):
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil_img = pil_img.filter(ImageFilter.GaussianBlur(radius=r))
    return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

def noise_attack(img, intensity):
    noise = np.random.normal(0, intensity, img.shape).astype(np.float32)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

def brightness_attack(img, factor):
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    enhancer = ImageEnhance.Brightness(pil_img)
    return cv2.cvtColor(np.array(enhancer.enhance(factor)), cv2.COLOR_RGB2BGR)

def scale_attack(img, scale):
    h, w = img.shape[:2]
    new_size = (int(w * scale), int(h * scale))
    resized = cv2.resize(img, new_size, interpolation=cv2.INTER_LANCZOS4)
    return cv2.resize(resized, (w, h), interpolation=cv2.INTER_LANCZOS4)

def rotate_attack(img, angle):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

def sharpen_attack(img):
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    return cv2.cvtColor(np.array(pil_img.filter(ImageFilter.SHARPEN)), cv2.COLOR_RGB2BGR)

def perspective_attack(img):
    h, w = img.shape[:2]
    pts1 = np.float32([[0,0], [w,0], [0,h], [w,h]])
    # Shift corners slightly to simulate 3D tilt
    pts2 = np.float32([[10,10], [w-20,15], [15,h-10], [w-10,h-20]])
    M = cv2.getPerspectiveTransform(pts1, pts2)
    return cv2.warpPerspective(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

if __name__ == "__main__":
    run_exhaustive_audit()
