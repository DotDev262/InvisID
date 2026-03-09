import cv2
import numpy as np
from imwatermark import WatermarkEncoder, WatermarkDecoder

def test_config(method):
    print(f"Testing {method} on Large Image...")
    # Very large image to ensure frequency space
    img = np.zeros((2000, 2000, 3), np.uint8)
    cv2.putText(img, 'INVISID FORENSIC TEST', (200, 1000), cv2.FONT_HERSHEY_SIMPLEX, 5, (255, 255, 255), 10)
    
    payload = b'EMP-001'
    
    try:
        encoder = WatermarkEncoder()
        encoder.set_watermark('bytes', payload)
        watermarked = encoder.encode(img, method)
        
        decoder = WatermarkDecoder('bytes', len(payload))
        extracted = decoder.decode(watermarked, method)
        
        res = extracted.decode(errors='ignore').replace('\x00', '')
        print(f"  Result: '{res}'")
        return res == payload.decode()
    except Exception as e:
        print(f"  Error: {e}")
        return False

if __name__ == "__main__":
    for m in ['dwtDct', 'dwtDctSvd']:
        test_config(m)
