import cv2
import numpy as np
import io
import os
from PIL import Image, ImageFilter, ImageEnhance
from app.services.image_service import embed_watermark, extract_watermark

def run_pen_test():
    print("--- InvisID Full-Suite Forensic Stress-Test ---")
    
    # 1. Setup Test Image
    img = np.random.randint(50, 200, (1024, 1024, 3), dtype=np.uint8)
    target_id = "EMP-999"
    print(f"Embedding ID: {target_id}")
    watermarked = embed_watermark(img, target_id)
    
    attacks = [
        ("Lossless PNG", lambda x: x),
        ("JPEG Compression (Q90)", lambda x: jpeg_attack(x, 90)),
        ("Gaussian Blur (R1)", lambda x: blur_attack(x, 1)),
        ("Brightness (+50%)", lambda x: brightness_attack(x, 1.5)),
        ("Contrast (+50%)", lambda x: contrast_attack(x, 1.5)),
        # Rotation and Scaling are extremely hard for spatial domain
        # but let's test a very light version
        ("Scaling (95%)", lambda x: scale_attack(x, 0.95)),
        ("COMBO: JPEG + Blur + Brightness", lambda x: brightness_attack(blur_attack(jpeg_attack(x, 90), 1), 1.2)),
        ("EXREME COMBO: All Vectors", lambda x: contrast_attack(brightness_attack(scale_attack(blur_attack(jpeg_attack(x, 85), 1), 0.98), 1.1), 1.1)),
        ("SCENARIO: WhatsApp/Social Media (High Comp + Scaling)", lambda x: scale_attack(jpeg_attack(x, 60), 0.5)),
        ("SCENARIO: Aggressive Edit (Blur + Contrast + Noise)", lambda x: contrast_attack(blur_attack(noise_attack(x, 10), 2), 1.5))
    ]
    
    for name, attack_func in attacks:
        print(f"\n[Test] {name}")
        attacked = attack_func(watermarked)
        extracted_id, conf = extract_watermark(attacked)
        status = "✅ PASS" if extracted_id == target_id else "❌ FAIL"
        print(f"  Result: '{extracted_id}' | Confidence: {conf*100}% | Status: {status}")

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

def brightness_attack(img, factor):
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    enhancer = ImageEnhance.Brightness(pil_img)
    return cv2.cvtColor(np.array(enhancer.enhance(factor)), cv2.COLOR_RGB2BGR)

def contrast_attack(img, factor):
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    enhancer = ImageEnhance.Contrast(pil_img)
    return cv2.cvtColor(np.array(enhancer.enhance(factor)), cv2.COLOR_RGB2BGR)

def noise_attack(img, intensity):
    noise = np.random.normal(0, intensity, img.shape).astype(np.uint8)
    return cv2.add(img, noise)

def scale_attack(img, scale):
    h, w = img.shape[:2]
    new_size = (int(w * scale), int(h * scale))
    resized = cv2.resize(img, new_size, interpolation=cv2.INTER_LANCZOS4)
    return cv2.resize(resized, (w, h), interpolation=cv2.INTER_LANCZOS4)

if __name__ == "__main__":
    run_pen_test()
