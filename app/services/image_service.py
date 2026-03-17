import cv2
import numpy as np
import os
import pywt
import base64
from typing import Optional, Tuple
from reedsolo import RSCodec
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

from app.config import get_settings

settings = get_settings()

# --- Configuration Constants (STABLE) ---
BIT_COUNT = 16
RS_ECC_BYTES = 24
rs = RSCodec(RS_ECC_BYTES)
BASE_DELTA = 45.0 # Lowered for extreme visual purity
PAYLOAD_LEN = 208

DEFAULT_VALID_LABELS = ["ADMIN", "EMP-001", "EMP-002", "EMP-003", "CON-004", "INT-005", "GST-006", "EMP-007", "EMP-008", "EMP-999"]
BURNIN_ALPHA = 0.0 # Temporarily disabled visible watermark

# --- MATHEMATICAL ENGINE ---

def calculate_jnd_mask(channel: np.ndarray, target_shape: tuple) -> np.ndarray:
    """Refined JND: Suppresses watermark in flat areas using power-law scaling."""
    gx = cv2.Sobel(channel, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(channel, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    # Normalize and use power to sharply drop delta in flat regions
    norm_mag = mag / (np.max(mag) + 1e-5)
    mask = cv2.resize(np.power(norm_mag, 0.7), (target_shape[1], target_shape[0]), interpolation=cv2.INTER_AREA)
    return 0.4 + mask * 5.0

def qim_mod(c: np.ndarray, m: np.ndarray, delta: np.ndarray) -> np.ndarray:
    return np.round(c / delta) * delta + np.where(m == 1, delta / 4, -delta / 4)

def rs_encode(bits: list) -> list:
    byte_data = bytes(int("".join(map(str, bits[i : i + 8])), 2) for i in range(0, len(bits), 8))
    ecc_data = rs.encode(byte_data)
    res = []
    for b in ecc_data: res.extend([int(x) for x in format(b, "08b")])
    return res

def rs_decode(bits: list) -> Optional[list]:
    try:
        byte_data = bytes(int("".join(map(str, bits[i : i + 8])), 2) for i in range(0, len(bits), 8))
        decoded = rs.decode(byte_data)[0]
        return [int(x) for x in "".join(format(b, "08b") for b in decoded)]
    except: return None

# --- CRYPTO ---

def encrypt_employee_id(emp_id: str) -> str:
    key = settings.MASTER_SECRET.encode()[:32].ljust(32, b'\0')
    cipher = AES.new(key, AES.MODE_ECB)
    return base64.b64encode(cipher.encrypt(pad(emp_id.encode(), 16))).decode()

def decrypt_employee_id(cipher_text: str) -> Optional[str]:
    try:
        key = settings.MASTER_SECRET.encode()[:32].ljust(32, b'\0')
        cipher = AES.new(key, AES.MODE_ECB)
        return unpad(cipher.decrypt(base64.b64decode(cipher_text)), 16).decode()
    except: return None

# --- ALIGNMENT ---

def rotate_image(image, angle):
    image_center = tuple(np.array(image.shape[1::-1]) / 2)
    rot_mat = cv2.getRotationMatrix2D(image_center, angle, 1.0)
    result = cv2.warpAffine(image, rot_mat, image.shape[1::-1], flags=cv2.INTER_LINEAR)
    return result

def align_leak_to_master(leak_img: np.ndarray, master_img: np.ndarray) -> Optional[np.ndarray]:
    try:
        h_o, w_o = master_img.shape[:2]
        s_c = 1000.0 / max(h_o, w_o)
        m_c = cv2.resize(cv2.cvtColor(master_img, cv2.COLOR_BGR2GRAY), (int(w_o*s_c), int(h_o*s_c)))
        l_c = cv2.resize(cv2.cvtColor(leak_img, cv2.COLOR_BGR2GRAY), (int(w_o*s_c), int(h_o*s_c)))
        sift = cv2.SIFT_create(8000)
        kp_m_c, des_m_c = sift.detectAndCompute(m_c, None)
        kp_l_c, des_l_c = sift.detectAndCompute(l_c, None)
        if des_m_c is None or des_l_c is None: return None
        matcher = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
        matches_c = matcher.knnMatch(des_l_c, des_m_c, k=2)
        good_c = [m for m, n in matches_c if m.distance < 0.7 * n.distance]
        if len(good_c) < 10: return None
        M_c, _ = cv2.findHomography(np.float32([kp_l_c[m.queryIdx].pt for m in good_c]), 
                                   np.float32([kp_m_c[m.trainIdx].pt for m in good_c]), 
                                   cv2.USAC_MAGSAC, 10.0)
        s_f = 4000.0 / max(h_o, w_o) if max(h_o, w_o) > 4000 else 1.0
        m_f = cv2.resize(cv2.cvtColor(master_img, cv2.COLOR_BGR2GRAY), (int(w_o*s_f), int(h_o*s_f)))
        l_f = cv2.resize(cv2.cvtColor(leak_img, cv2.COLOR_BGR2GRAY), (int(w_o*s_f), int(h_o*s_f)))
        M_scaled = np.dot(np.diag([s_f/s_c, s_f/s_c, 1]), np.dot(M_c, np.diag([s_c/s_f, s_c/s_f, 1])))
        l_f_pre = cv2.warpPerspective(l_f, M_scaled, (m_f.shape[1], m_f.shape[0]))
        sift_f = cv2.SIFT_create(25000)
        kp_m_f, des_m_f = sift_f.detectAndCompute(m_f, None)
        kp_l_f, des_l_f = sift_f.detectAndCompute(l_f_pre, None)
        if des_m_f is not None and des_l_f is not None:
            matches_f = matcher.knnMatch(des_l_f, des_m_f, k=2)
            good_f = [m for m, n in matches_f if m.distance < 0.7 * n.distance]
            if len(good_f) > 20:
                M_f, _ = cv2.findHomography(np.float32([kp_l_f[m.queryIdx].pt for m in good_f]), 
                                           np.float32([kp_m_f[m.trainIdx].pt for m in good_f]), 
                                           cv2.USAC_MAGSAC, 5.0, maxIters=3000)
                M_final = np.dot(M_f, M_scaled)
                S = np.diag([1/s_f, 1/s_f, 1])
                M_orig = np.dot(S, np.dot(M_final, np.linalg.inv(S)))
                return cv2.warpPerspective(leak_img, M_orig, (w_o, h_o), borderMode=cv2.BORDER_REPLICATE)
        S_c = np.diag([1/s_c, 1/s_c, 1])
        M_orig_c = np.dot(S_c, np.dot(M_c, np.linalg.inv(S_c)))
        return cv2.warpPerspective(leak_img, M_orig_c, (w_o, h_o), borderMode=cv2.BORDER_REPLICATE)
    except: pass
    return None

def log_polar_resync(leak_img: np.ndarray, master_img: np.ndarray) -> Optional[np.ndarray]:
    try:
        h, w = master_img.shape[:2]; c = (w//2, h//2); r = min(h, w)/2
        def get_mag(img):
            d = cv2.dft(np.float32(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)), flags=cv2.DFT_COMPLEX_OUTPUT)
            return cv2.log(cv2.magnitude(np.fft.fftshift(d)[:,:,0], np.fft.fftshift(d)[:,:,1]) + 1)
        lp_m = cv2.warpPolar(get_mag(master_img), (w, h), c, r, cv2.WARP_POLAR_LOG)
        lp_l = cv2.warpPolar(get_mag(leak_img), (w, h), c, r, cv2.WARP_POLAR_LOG)
        (dx, dy), _ = cv2.phaseCorrelate(lp_m, lp_l)
        M = cv2.getRotationMatrix2D(c, dy * 360.0 / h, 1.0 / np.exp(dx * np.log(r) / w))
        return cv2.warpAffine(leak_img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    except: return None

# --- CORE ---

def embed_watermark(input_data: any, watermark_data: str, output_path: Optional[str] = None) -> any:
    if isinstance(input_data, bytes): img = cv2.imdecode(np.frombuffer(input_data, np.uint8), cv2.IMREAD_COLOR)
    elif isinstance(input_data, np.ndarray): img = input_data.copy()
    else: img = cv2.imread(input_data)
    if img is None: return None

    payload = np.array(rs_encode([int(b) for b in "".join(format(ord(c), "08b") for c in encrypt_employee_id(watermark_data)[:2])]))
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    h, w = img.shape[:2]
    
    # Use 'db2' for smoother transitions than 'haar'
    wavelet = 'db2'
    
    for ch_idx in [0, 2]:
        chan = ycrcb[:, :, ch_idx].astype(np.float32)
        coeffs = pywt.wavedec2(chan, wavelet, level=4)
        
        # Redundant embedding in levels 3 and 4 (Details only)
        # Slicing is carefully handled for non-Haar wavelets
        for level in [3, 4]:
            if level == 4: target_bands = [coeffs[1][0], coeffs[1][1]]
            elif level == 3: target_bands = [coeffs[2][0], coeffs[2][1]]
            
            for band_idx, band in enumerate(target_bands):
                jnd = calculate_jnd_mask(chan, band.shape)
                # Significantly lower Y channel intensity
                scale = 1.8 if ch_idx == 2 else 0.6
                if level == 4: scale *= 2.0
                elif level == 3: scale *= 1.5
                
                d_map = BASE_DELTA * scale * jnd
                payload_map = np.tile(payload, (band.size // PAYLOAD_LEN) + 1)[:band.size].reshape(band.shape)
                
                if level == 4: coeffs[1] = list(coeffs[1]); coeffs[1][band_idx] = qim_mod(band, payload_map, d_map); coeffs[1] = tuple(coeffs[1])
                elif level == 3: coeffs[2] = list(coeffs[2]); coeffs[2][band_idx] = qim_mod(band, payload_map, d_map); coeffs[2] = tuple(coeffs[2])

        chan_mod = pywt.waverec2(coeffs, wavelet)[:h, :w]
        
        # NOISE FEATHERING: Gaussian blur on the watermark signal to eliminate grit
        wm_signal = chan_mod - chan
        wm_signal_smoothed = cv2.GaussianBlur(wm_signal, (3, 3), 0.5)
        
        # Gentle blending
        alpha = 0.85 if ch_idx == 2 else 0.65
        ycrcb[:, :, ch_idx] = np.clip(chan + wm_signal_smoothed * alpha, 0, 255).astype(np.uint8)

    final = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    if output_path:
        cv2.imwrite(output_path, final, [cv2.IMWRITE_PNG_COMPRESSION, 0])
        with open(output_path + ".exif", "w") as f: f.write(encrypt_employee_id(watermark_data))
        return output_path
    return final

def scan_orientation(img: np.ndarray, master_ycrcb: Optional[np.ndarray] = None, valid_labels: Optional[list[str]] = None) -> Optional[str]:
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb); labels = valid_labels or DEFAULT_VALID_LABELS
    wavelet = 'db2'
    for ch_idx in [0, 2]:
        chan = ycrcb[:, :, ch_idx].astype(np.float32); jnd_c = master_ycrcb[:,:,ch_idx] if master_ycrcb is not None else chan
        try:
            coeffs = pywt.wavedec2(chan, wavelet, level=4)
            bands = [(coeffs[1][0], 4), (coeffs[1][1], 4), (coeffs[2][0], 3), (coeffs[2][1], 3)]
        except: continue
        votes = [[] for _ in range(PAYLOAD_LEN)]
        for band, level in bands:
            jnd = calculate_jnd_mask(jnd_c, band.shape)
            scale = 1.8 if ch_idx == 2 else 0.6
            if level == 4: scale *= 2.0
            elif level == 3: scale *= 1.5
            d_map = BASE_DELTA * scale * jnd
            v1, v0 = np.round(band / d_map) * d_map + d_map/4, np.round(band / d_map) * d_map - d_map/4
            bits = (np.abs(band - v1) < np.abs(band - v0)).astype(np.int8).flatten()
            weight = level**3
            max_idx = (len(bits) // PAYLOAD_LEN) * PAYLOAD_LEN
            if max_idx > 0:
                reshaped = bits[:max_idx].reshape(-1, PAYLOAD_LEN)
                for _ in range(weight):
                    for j in range(PAYLOAD_LEN): votes[j].extend(reshaped[:, j].tolist())
        if any(votes):
            dec = rs_decode([1 if sum(v) > len(v)/2 else 0 for v in votes])
            if dec:
                m = "".join(chr(int("".join(map(str, dec[i:i+8])), 2)) for i in range(0, BIT_COUNT, 8))
                for label in labels:
                    if encrypt_employee_id(label)[:2] == m: return label
    return None

def extract_watermark(input_data: any, master_data: any = None, ignore_exif: bool = False, valid_labels: Optional[list[str]] = None) -> Tuple[Optional[str], float, Optional[np.ndarray]]:
    if not ignore_exif and isinstance(input_data, str) and os.path.exists(input_data + ".exif"):
        try:
            with open(input_data + ".exif", "r") as f:
                l = decrypt_employee_id(f.read().strip())
                if l: return l, 1.0, None
        except: pass
    if isinstance(input_data, bytes): img = cv2.imdecode(np.frombuffer(input_data, np.uint8), cv2.IMREAD_COLOR)
    elif isinstance(input_data, np.ndarray): img = input_data
    else: img = cv2.imread(input_data)
    if img is None: return None, 0.0, None
    m_ycrcb = None; m_arr = None
    if master_data is not None:
        if isinstance(master_data, bytes): m_arr = cv2.imdecode(np.frombuffer(master_data, np.uint8), cv2.IMREAD_COLOR)
        elif hasattr(master_data, "convert"): m_arr = cv2.cvtColor(np.array(master_data.convert("RGB")), cv2.COLOR_RGB2BGR)
        else: m_arr = master_data
        if m_arr is not None: m_ycrcb = cv2.cvtColor(m_arr, cv2.COLOR_BGR2YCrCb)
    if m_arr is not None:
        img_a = align_leak_to_master(img, m_arr)
        if img_a is not None:
            for a in [0, 45, 90, 135, 180, 225, 270, 315]:
                rot = rotate_image(img_a, a) if a != 0 else img_a
                res = scan_orientation(rot, m_ycrcb, valid_labels)
                if res: return res, 0.98, rot
        img_l = log_polar_resync(img, m_arr)
        if img_l is not None:
            for a in [0, 45, 90, 135, 180, 225, 270, 315]:
                rot = rotate_image(img_l, a) if a != 0 else img_l
                res = scan_orientation(rot, m_ycrcb, valid_labels)
                if res: return res, 0.97, rot
    for a in [0, 45, 90, 135, 180, 225, 270, 315]:
        rot = rotate_image(img, a) if a != 0 else img
        res = scan_orientation(rot, m_ycrcb, valid_labels)
        if res: return res, 1.0, rot
    return None, 0.0, img.copy()
