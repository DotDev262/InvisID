import cv2
import numpy as np
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from app.config import get_settings

settings = get_settings()

# Forensic Constants
BLOCK_SIZE = 16 
BIT_COUNT = 16 

def get_crypto_key():
    return settings.MASTER_SECRET.encode()[:32].ljust(32, b'\0')

def encrypt_employee_id(emp_id: str) -> str:
    key = get_crypto_key()
    cipher = AES.new(key, AES.MODE_ECB)
    ct_bytes = cipher.encrypt(pad(emp_id.encode(), AES.block_size))
    return base64.b64encode(ct_bytes).decode('utf-8')

def decrypt_employee_id(cipher_text: str) -> str:
    try:
        key = get_crypto_key()
        cipher = AES.new(key, AES.MODE_ECB)
        decoded_ct = base64.b64decode(cipher_text)
        pt = unpad(cipher.decrypt(decoded_ct), AES.block_size)
        return pt.decode('utf-8')
    except: return "UNKNOWN"

def align_leak_to_master(leak_img: np.ndarray, master_img: np.ndarray) -> np.ndarray:
    """
    Advanced Forensic Alignment using SIFT + Flann Matcher.
    Significantly more robust than ORB for 3D tilts and high noise.
    """
    try:
        # SIFT is the industry standard for robust feature matching
        sift = cv2.SIFT_create(8000)
        kp1, des1 = sift.detectAndCompute(leak_img, None)
        kp2, des2 = sift.detectAndCompute(master_img, None)

        # FLANN parameters for high-precision matching
        FLANN_INDEX_KDTREE = 1
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        
        matches = flann.knnMatch(des1, des2, k=2)

        # Lowe's ratio test to filter good matches
        good = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good.append(m)

        if len(good) > 10:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            
            h, w, _ = master_img.shape
            aligned = cv2.warpPerspective(leak_img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
            return aligned
    except Exception as e:
        print(f"Deep Alignment Error: {e}")
    return leak_img

def embed_watermark(input_data: any, watermark_data: str, output_path: str = None) -> any:
    """Standard Differential-Mean Embedding."""
    if isinstance(input_data, bytes):
        nparr = np.frombuffer(input_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    elif isinstance(input_data, np.ndarray):
        img = input_data.copy()
    else:
        img = cv2.imread(input_data)

    if img is None: raise ValueError("Invalid image")

    cipher = encrypt_employee_id(watermark_data)
    bits = "".join(format(ord(c), '08b') for c in cipher[:2])
    bit_array = [int(b) for b in bits]

    h, w, _ = img.shape
    watermarked = img.astype(np.float32)
    strength = 25
    
    for quad in range(4):
        r_off = (quad // 2) * (h // 2)
        c_off = (quad % 2) * (w // 2)
        idx = 0
        for r in range(r_off + BLOCK_SIZE, r_off + (h // 2) - BLOCK_SIZE, BLOCK_SIZE):
            for c in range(c_off + BLOCK_SIZE, c_off + (w // 2) - (BLOCK_SIZE * 2), BLOCK_SIZE * 2):
                if idx < len(bit_array):
                    bit = bit_array[idx]
                    if bit == 1:
                        watermarked[r:r+BLOCK_SIZE, c:c+BLOCK_SIZE, 1] += strength
                        watermarked[r:r+BLOCK_SIZE, c+BLOCK_SIZE:c+(BLOCK_SIZE*2), 1] -= strength
                    else:
                        watermarked[r:r+BLOCK_SIZE, c:c+BLOCK_SIZE, 1] -= strength
                        watermarked[r:r+BLOCK_SIZE, c+BLOCK_SIZE:c+(BLOCK_SIZE*2), 1] += strength
                    idx += 1
                else: break
            if idx >= len(bit_array): break

    watermarked = np.clip(watermarked, 0, 255).astype(np.uint8)
    if output_path:
        cv2.imwrite(output_path, watermarked)
        return output_path
    return watermarked

def scan_orientation(img: np.ndarray) -> str:
    """Helper to perform extraction on a specific orientation."""
    h, w, _ = img.shape
    global_labels = ["ADMIN", "EMP-001", "EMP-002", "EMP-003", "CON-004", "INT-005", "GST-006", "EMP-007", "EMP-008", "EMP-999"]
    
    for quad in range(4):
        r_off = (quad // 2) * (h // 2)
        c_off = (quad % 2) * (w // 2)
        extracted_bits = []
        for r in range(r_off + BLOCK_SIZE, r_off + (h // 2) - BLOCK_SIZE, BLOCK_SIZE):
            for c in range(c_off + BLOCK_SIZE, c_off + (w // 2) - (BLOCK_SIZE * 2), BLOCK_SIZE * 2):
                if len(extracted_bits) < BIT_COUNT:
                    mean_a = np.mean(img[r:r+BLOCK_SIZE, c:c+BLOCK_SIZE, 1])
                    mean_b = np.mean(img[r:r+BLOCK_SIZE, c+BLOCK_SIZE:c+(BLOCK_SIZE*2), 1])
                    extracted_bits.append(1 if mean_a > mean_b else 0)
                else: break
            if len(extracted_bits) >= BIT_COUNT: break
            
        if len(extracted_bits) == BIT_COUNT:
            chars = []
            for i in range(0, len(extracted_bits), 8):
                byte = "".join(map(str, extracted_bits[i:i+8]))
                chars.append(chr(int(byte, 2)))
            marker = "".join(chars)
            for label in global_labels:
                if encrypt_employee_id(label)[:2] == marker:
                    return label
    return None

def extract_watermark(input_data: any, master_data: any = None) -> tuple[str, float]:
    """Forensic Extraction with High-Precision Alignment."""
    if isinstance(input_data, bytes):
        nparr = np.frombuffer(input_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    elif isinstance(input_data, np.ndarray):
        img = input_data
    else:
        img = cv2.imread(input_data)

    if img is None: return "", 0.0

    # STAGE 0: High-Precision Alignment if Master is available
    if master_data is not None:
        if isinstance(master_data, bytes):
            m_arr = cv2.imdecode(np.frombuffer(master_data, np.uint8), cv2.IMREAD_COLOR)
        else: m_arr = master_data
        img = align_leak_to_master(img, m_arr)

    # STAGE 1: Standard orientations
    for angle in [0, 90, 180, 270]:
        if angle == 0: rotated = img
        else: rotated = np.rot90(img, angle // 90)
        res = scan_orientation(rotated)
        if res: return res, 1.0

    # STAGE 2: Deep scan if Stage 1 fails (handles micro-rotations)
    h, w = img.shape[:2]
    for angle in [-15, 15, -10, 10]:
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
        rotated = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        res = scan_orientation(rotated)
        if res: return res, 0.95

    return "UNKNOWN", 0.0
