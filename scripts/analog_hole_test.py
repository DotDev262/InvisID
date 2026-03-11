import cv2
import numpy as np
import io
import os
import sys
from PIL import Image, ImageEnhance

# Add root to path
sys.path.append(os.getcwd())

from app.services.image_service import embed_watermark, extract_watermark

def simulate_analog_hole(img):
    """
    Simulates a smartphone photo of a screen:
    1. Geometric Perspective Warp
    2. Moiré Pattern (High-frequency interference)
    3. Luminance Washout (Screen glow)
    4. Sensor Noise
    """
    h, w = img.shape[:2]
    
    # 1. Geometric Warp (Handheld tilt)
    pts1 = np.float32([[0,0], [w,0], [0,h], [w,h]])
    pts2 = np.float32([[w*0.05, h*0.05], [w*0.92, h*0.08], [w*0.02, h*0.95], [w*0.98, h*0.92]])
    M = cv2.getPerspectiveTransform(pts1, pts2)
    img = cv2.warpPerspective(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    
    # 2. Moiré Pattern Simulation
    # Creates periodic horizontal/vertical lines like a screen's pixel grid
    moire = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(0, h, 4): moire[i:i+1, :, :] = 20
    for j in range(0, w, 4): moire[:, j:j+1, :] = 20
    img = cv2.addWeighted(img, 0.9, moire, 0.1, 0)
    
    # 3. Luminance Washout & Contrast Loss
    pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    enhancer = ImageEnhance.Brightness(pil_img)
    pil_img = enhancer.enhance(1.3) # Screen glow
    enhancer = ImageEnhance.Contrast(pil_img)
    pil_img = enhancer.enhance(0.7) # Contrast loss
    
    # 4. Final Sensor Noise
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    noise = np.random.normal(0, 5, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return img

def run_analog_audit():
    print("\n📸 --- InvisID 'Analog Hole' Forensic Audit (Real 4K Asset) --- 📸")
    
    # Load Real 4K Asset
    from app.config import get_settings
    from app.utils.crypto import decrypt_data
    s = get_settings()
    asset_path = os.path.join(s.UPLOAD_DIR, "b0ce1125-e9b4-4f1d-992b-e89ee01a98f7.png")
    
    with open(asset_path, "rb") as f:
        img_data = decrypt_data(f.read())
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    target_id = "EMP-001"
    print(f"[*] Embedding Identity: {target_id}")
    watermarked = embed_watermark(img, target_id)
    
    print("[*] Simulating 'Smartphone Photo of Screen' Attack...")
    attacked = simulate_analog_hole(watermarked)
    
    # Save for visual inspection
    cv2.imwrite("scripts/analog_hole_simulation.png", attacked)
    print("[+] Attack simulation saved to scripts/analog_hole_simulation.png")
    
    print("[*] Attempting Forensic Recovery (ASIFT + Log-Polar + Moiré Filter)...")
    
    # Let's explicitly test the alignment engine's output
    from app.services.image_service import align_leak_to_master
    aligned_debug = align_leak_to_master(attacked, img)
    cv2.imwrite("scripts/analog_hole_aligned_debug.png", aligned_debug)
    print("[+] Alignment debug saved to scripts/analog_hole_aligned_debug.png")

    extracted_id, conf = extract_watermark(attacked, master_data=img, ignore_exif=True)
    
    status = "✅ PASS" if extracted_id == target_id else "❌ FAIL (MATH)"
    print(f"\n==================================================")
    print(f"MATH RESULT: '{extracted_id}'")
    print(f"CONFIDENCE: {conf*100:.1f}%")
    print(f"HYBRID STATUS: {status}")
    print(f"--------------------------------------------------")
    print(f"ACTION: Please open 'scripts/analog_hole_simulation.png'.")
    print(f"        If you can see '{target_id}' faintly in the photo,")
    print(f"        the Hybrid Burn-In layer has SUCCEEDED.")
    print(f"==================================================\n")

if __name__ == "__main__":
    run_analog_audit()
