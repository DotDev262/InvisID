import os
import requests
import time
from PIL import Image, ImageFilter, ImageOps
import io
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000/api"
ADMIN_KEY = "admin-secret-key"
EMPLOYEE_KEY = "employee-secret-key"

def run_test(name, attack_fn):
    print(f"\n[+] Testing: {name}...")
    
    # 1. Get images
    resp = requests.get(f"{BASE_URL}/images/", headers={"X-API-Key": EMPLOYEE_KEY})
    if not resp.ok or not resp.json():
        print("[-] Error: No images available. Please upload a master image first.")
        return
    
    target_img = resp.json()[0]
    image_id = target_img['id']
    
    # 2. Download watermarked image
    print(f"[*] Downloading watermarked image: {target_img['filename']}...")
    resp = requests.get(f"{BASE_URL}/images/{image_id}/download", headers={"X-API-Key": EMPLOYEE_KEY})
    if not resp.ok:
        print(f"[-] Download failed: {resp.text}")
        return
    
    original_data = resp.content
    img = Image.open(io.BytesIO(original_data))
    
    # 3. Apply Attack
    print(f"[*] Applying attack: {name}...")
    attacked_img_io = attack_fn(img)
    
    # 4. Investigate (Upload to Lab)
    print(f"[*] Uploading to Investigation Lab...")
    files = {"file": ("leaked.jpg", attacked_img_io, "image/jpeg")}
    resp = requests.post(f"{BASE_URL}/investigate", headers={"X-API-Key": ADMIN_KEY}, files=files)
    
    if not resp.ok:
        print(f"[-] Investigation failed to start: {resp.text}")
        return
        
    job_id = resp.json()["job_id"]
    
    # 5. Poll result
    print(f"[*] Polling job status: {job_id}...")
    while True:
        resp = requests.get(f"{BASE_URL}/jobs/{job_id}", headers={"X-API-Key": ADMIN_KEY})
        job = resp.json()
        if job["status"] == "completed":
            res = job["result"]
            print(f"[!] SUCCESS: Identified {res['leaked_by']} with {res['confidence']*100}% confidence.")
            break
        elif job["status"] == "failed":
            print(f"[-] FAILED: {job['error']}")
            break
        time.sleep(1)

# Attack Functions
def attack_jpeg_50(img):
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=50)
    out.seek(0)
    return out

def attack_blur(img):
    out = io.BytesIO()
    blurred = img.filter(ImageFilter.GaussianBlur(radius=2))
    blurred.save(out, format="JPEG")
    out.seek(0)
    return out

def attack_crop(img):
    out = io.BytesIO()
    w, h = img.size
    # Crop 20% from the edges
    cropped = img.crop((w*0.1, h*0.1, w*0.9, h*0.9))
    cropped.save(out, format="JPEG")
    out.seek(0)
    return out

def main():
    print("=== InvisID Forensic Attack Simulator ===")
    
    tests = [
        ("JPEG Compression (Q=50)", attack_jpeg_50),
        ("Gaussian Blur (R=2)", attack_blur),
        ("Geometric Crop (20%)", attack_crop)
    ]
    
    for name, fn in tests:
        try:
            run_test(name, fn)
        except Exception as e:
            print(f"[-] Error during {name}: {str(e)}")

if __name__ == "__main__":
    main()
