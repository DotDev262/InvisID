import cv2
import numpy as np
import os
import sys
sys.path.insert(0, '/home/aryan/Code/Projects/InvisID')
from app.services.image_service import embed_watermark
from app.config import get_settings
from app.utils.crypto import decrypt_data

def calculate_psnr(original, watermarked):
    mse = np.mean((original.astype(np.float32) - watermarked.astype(np.float32)) ** 2)
    if mse == 0:
        return float('inf')
    max_pixel = 255.0
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return psnr

def test_current_psnr():
    settings = get_settings()
    upload_dir = settings.UPLOAD_DIR
    files = [f for f in os.listdir(upload_dir) if f.endswith('.png') and not f.startswith('test_wm_')]
    
    if not files:
        print("No master images found to test PSNR.")
        return

    for file in files[:3]:
        path = os.path.join(upload_dir, file)
        with open(path, "rb") as f:
            decrypted = decrypt_data(f.read())
        original = cv2.imdecode(np.frombuffer(decrypted, np.uint8), cv2.IMREAD_COLOR)
        
        target_id = "EMP-001"
        watermarked = embed_watermark(original, target_id)
        
        psnr = calculate_psnr(original, watermarked)
        print(f"File: {file} | PSNR: {psnr:.2f} dB")

if __name__ == "__main__":
    test_current_psnr()
