import cv2
import numpy as np
import os
import sys

# Add current dir to path
sys.path.append(os.getcwd())

from app.services.image_service import embed_watermark, extract_watermark

def test_robustness():
    print("--- DWT-QIM Forensic Robustness Test ---")
    
    # 1. Setup Test Image
    img = np.zeros((1024, 1024, 3), dtype=np.uint8)
    for i in range(0, 1024, 64):
        cv2.line(img, (i, 0), (i, 1024), (255, 255, 255), 2)
        cv2.line(img, (0, i), (1024, i), (255, 255, 255), 2)
    cv2.putText(img, "InvisID DWT", (100, 500), cv2.FONT_HERSHEY_SIMPLEX, 4, (255, 255, 255), 10)
    
    target_id = "EMP-999"
    print(f"Embedding ID: {target_id}")
    watermarked = embed_watermark(img, target_id)
    
    attacks = [
        ("Lossless Baseline", lambda x: x),
        ("JPEG Compression (Q80)", lambda x: jpeg_attack(x, 80)),
        ("Downscale (50%)", lambda x: scale_attack(x, 0.5)),
        ("Rotation (15°)", lambda x: rotate_attack(x, 15)),
        ("Gaussian Blur (R1)", lambda x: cv2.GaussianBlur(x, (3, 3), 1)),
    ]
    
    for name, attack_func in attacks:
        print(f"\n[Test] {name}")
        attacked = attack_func(watermarked)
        # Use master alignment
        extracted_id, conf = extract_watermark(attacked, master_data=img, ignore_exif=True)
        status = "✅ PASS" if extracted_id == target_id else "❌ FAIL"
        print(f"  Result: '{extracted_id}' | Confidence: {conf*100}% | Status: {status}")

def jpeg_attack(img, q):
    import io
    from PIL import Image
    buf = io.BytesIO()
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    pil_img.save(buf, format="JPEG", quality=q)
    buf.seek(0)
    return cv2.cvtColor(np.array(Image.open(buf)), cv2.COLOR_RGB2BGR)

def scale_attack(img, scale):
    h, w = img.shape[:2]
    new_size = (int(w * scale), int(h * scale))
    return cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)

def rotate_attack(img, angle):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)

if __name__ == "__main__":
    test_robustness()
