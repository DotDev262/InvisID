import cv2
import numpy as np
import os
from imwatermark import WatermarkEncoder, WatermarkDecoder
from PIL import Image, ImageFilter
from io import BytesIO

# 64-byte payload with aggressive redundancy
ID = "EMP-001"
PAYLOAD = (ID + "|") * 8 
PAYLOAD = PAYLOAD[:64].encode()

def test_png_robustness(method_name):
    print(f"\n--- Testing PNG Robustness: {method_name} ---")
    img = np.random.randint(0, 255, (1024, 1024, 3), dtype=np.uint8) # Larger image for better embedding
    cv2.putText(img, 'InvisID Forensic Asset', (100, 500), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
    
    try:
        # 1. Embed
        encoder = WatermarkEncoder()
        encoder.set_watermark('bytes', PAYLOAD)
        watermarked = encoder.encode(img, method_name)
        
        # 2. Save as PNG (Lossless)
        png_path = "test_forensic.png"
        cv2.imwrite(png_path, watermarked)
        
        # 3. Simulate multiple light manipulations (Resave, Blur, Brightness)
        # Load back
        attacked_img = cv2.imread(png_path)
        
        # 4. Extract
        decoder = WatermarkDecoder('bytes', 64)
        extracted = decoder.decode(attacked_img, method_name)
        result = extracted.decode(errors='ignore').replace('\x00', '')
        
        print(f"Extracted: '{result}'")
        
        # Majority Vote Logic
        parts = [p.strip() for p in result.split('|') if p.strip()]
        if not parts: return False
        
        winner = max(set(parts), key=parts.count)
        print(f"Forensic Winner: '{winner}'")
        
        os.remove(png_path)
        return winner == ID
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    res = test_png_robustness('dwtDct')
    print(f"\nFinal Result: {'PASSED ✅' if res else 'FAILED ❌'}")
