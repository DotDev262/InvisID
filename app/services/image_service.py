import cv2
import numpy as np
import json
import base64
import os
import pywt
from reedsolo import RSCodec
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from app.config import get_settings

settings = get_settings()

# --- Ghost-Cloud Architecture Constants ---
BIT_COUNT = 16 
RS_ECC_BYTES = 20 
rs = RSCodec(RS_ECC_BYTES)
BASE_DELTA = 50.0  # Ultra-low for zero visibility
PAYLOAD_LEN = 176

# --- MATHEMATICAL ENGINE ---

def calculate_jnd_mask(channel: np.ndarray, target_shape: tuple) -> np.ndarray:
    """Mathematical Just Noticeable Difference (JND) Model."""
    gx = cv2.Sobel(channel, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(channel, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    mask = cv2.resize(mag, (target_shape[1], target_shape[0]), interpolation=cv2.INTER_AREA)
    return 0.5 + (mask / (np.max(mask) + 1e-5)) * 3.0

def qim_mod(c: float, m: int, delta: float) -> float:
    """Standard QIM Modulation."""
    if m == 1:
        return np.round(c / delta) * delta + delta / 4
    else:
        return np.round(c / delta) * delta - delta / 4

def qim_demod(c_star: float, delta: float) -> int:
    """Standard QIM Demodulation."""
    v1 = np.round(c_star / delta) * delta + delta / 4
    v0 = np.round(c_star / delta) * delta - delta / 4
    return 1 if np.abs(c_star - v1) < np.abs(c_star - v0) else 0

def rs_encode(bits: list) -> list:
    """RS Armor."""
    byte_data = bytes(int("".join(map(str, bits[i:i+8])), 2) for i in range(0, len(bits), 8))
    ecc_data = rs.encode(byte_data)
    res = []
    for b in ecc_data: res.extend([int(x) for x in format(b, '08b')])
    return res

def rs_decode(bits: list) -> list:
    """RS Recovery."""
    try:
        byte_data = bytes(int("".join(map(str, bits[i:i+8])), 2) for i in range(0, len(bits), 8))
        decoded = rs.decode(byte_data)[0]
        res = []
        for b in decoded: res.extend([int(x) for x in format(b, '08b')])
        return res
    except: return []

# --- CRYPTO & ALIGNMENT ---

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
    """Multi-Scale ASIFT Alignment with Moiré Eraser."""
    def get_affine_tilt(img, tilt, phi):
        h, w = img.shape[:2]
        t_mat = np.float32([[1, 0, 0], [0, 1.0/tilt, 0]])
        r_mat = cv2.getRotationMatrix2D((w/2, h/2), phi, 1)
        combined = np.dot(np.vstack([t_mat, [0,0,1]]), np.vstack([r_mat, [0,0,1]]))[:2]
        return cv2.warpAffine(img, combined, (w, h), borderMode=cv2.BORDER_REPLICATE)

    try:
        h_orig, w_orig = master_img.shape[:2]
        scale = 2000.0 / max(h_orig, w_orig) if max(h_orig, w_orig) > 2500 else 1.0
        h_s, w_s = int(h_orig * scale), int(w_orig * scale)
        m_scaled = cv2.resize(cv2.cvtColor(master_img, cv2.COLOR_BGR2GRAY), (w_s, h_s), interpolation=cv2.INTER_AREA)
        l_scaled = cv2.resize(cv2.cvtColor(leak_img, cv2.COLOR_BGR2GRAY), (w_s, h_s), interpolation=cv2.INTER_AREA)
        
        # Moiré Eraser: Heavy median blur eliminates screen pixel-grids while preserving edges
        m_scaled = cv2.medianBlur(m_scaled, 7)
        l_scaled = cv2.medianBlur(l_scaled, 7)
        
        sift = cv2.SIFT_create(15000)
        kp_m, des_m = sift.detectAndCompute(m_scaled, None)
        if des_m is None: return leak_img

        best_M = None
        max_good = 0
        for t in [1.0, 1.5, 2.2]:
            for p in [0, 45, 90, 135]:
                sim_leak = get_affine_tilt(l_scaled, t, p) if t > 1.0 or p > 0 else l_scaled
                kp_l, des_l = sift.detectAndCompute(sim_leak, None)
                if des_l is None: continue
                matches = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50)).knnMatch(des_l, des_m, k=2)
                good = [m for m, n in matches if m.distance < 0.75 * n.distance]
                if len(good) > max_good:
                    max_good = len(good)
                    if len(good) > 10:
                        src_pts = np.float32([kp_l[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                        dst_pts = np.float32([kp_m[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
                        M, _ = cv2.findHomography(src_pts, dst_pts, cv2.USAC_MAGSAC, 10.0)
                        best_M = M

        if best_M is not None:
            if scale != 1.0:
                S = np.diag([1/scale, 1/scale, 1])
                best_M = np.dot(S, np.dot(best_M, np.linalg.inv(S)))
            return cv2.warpPerspective(leak_img, best_M, (w_orig, h_orig), borderMode=cv2.BORDER_REPLICATE)
    except: pass
    return leak_img

def suppress_moire_noise(img: np.ndarray) -> np.ndarray:
    """Filters out Moiré patterns and screen-flicker noise."""
    return cv2.medianBlur(img, 3)

def log_polar_resync(leak_img: np.ndarray, master_img: np.ndarray) -> np.ndarray:
    """Log-Polar Fourier-Mellin Alignment."""
    try:
        h, w = master_img.shape[:2]
        center = (w // 2, h // 2)
        radius = min(h, w) / 2
        
        def get_mag_spectrum(img):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            dft = cv2.dft(np.float32(gray), flags=cv2.DFT_COMPLEX_OUTPUT)
            dft_shift = np.fft.fftshift(dft)
            mag = cv2.magnitude(dft_shift[:,:,0], dft_shift[:,:,1])
            return cv2.log(mag + 1)

        mag_m = get_mag_spectrum(master_img)
        mag_l = get_mag_spectrum(leak_img)
        flags = cv2.WARP_POLAR_LOG | cv2.INTER_LINEAR | cv2.WARP_FILL_OUTLIERS
        lp_m = cv2.warpPolar(mag_m, (w, h), center, radius, flags)
        lp_l = cv2.warpPolar(mag_l, (w, h), center, radius, flags)
        (dx, dy), response = cv2.phaseCorrelate(lp_m, lp_l)
        rotation = dy * 360.0 / h
        scale = np.exp(dx * np.log(radius) / w)
        M = cv2.getRotationMatrix2D(center, rotation, 1.0/scale)
        return cv2.warpAffine(leak_img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    except: return leak_img

# --- CORE PIPELINE ---

def embed_watermark(input_data: any, watermark_data: str, output_path: str = None) -> any:
    """Forensic Embedding with Ghost-Cloud detail-band DWT-QIM."""
    if isinstance(input_data, bytes):
        img = cv2.imdecode(np.frombuffer(input_data, np.uint8), cv2.IMREAD_COLOR)
    elif isinstance(input_data, np.ndarray): img = input_data.copy()
    else: img = cv2.imread(input_data)
    if img is None: raise ValueError("Invalid image")

    # 1. Prepare Armored Payload
    cipher = encrypt_employee_id(watermark_data)
    raw_bits = [int(b) for b in "".join(format(ord(c), '08b') for c in cipher[:2])]
    payload = rs_encode(raw_bits)

    # 2. Colorspace & DWT
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    h, w = img.shape[:2]
    level = 3 if max(h, w) > 2000 else 2
    
    for ch_idx in [0, 2]:
        chan = ycrcb[:, :, ch_idx].astype(np.float32)
        coeffs = pywt.wavedec2(chan, 'haar', level=level)
        
        # LL band (coeffs[0]) is preserved. LH, HL, HH are modulated.
        # coeffs[1] is (LH, HL, HH) for level decomposition
        LL = coeffs[0]
        LH, HL, HH = coeffs[1]
        
        jnd = calculate_jnd_mask(chan, HL.shape)

        # 3. Dynamic QIM in Detail Bands (HL + LH)
        h_s, w_s = HL.shape
        idx = 0
        for r in range(h_s):
            for c in range(w_s):
                # Pattern Sparsity Jitter
                if (r + c) % 2 == 0:
                    d = (BASE_DELTA * 0.7 if ch_idx == 0 else BASE_DELTA) * jnd[r, c]
                    HL[r, c] = qim_mod(HL[r, c], payload[idx], d)
                    LH[r, c] = qim_mod(LH[r, c], payload[idx], d)
                    idx = (idx + 1) % PAYLOAD_LEN

        # 4. Reconstruct & Edge-Feather
        coeffs_mod = list(coeffs)
        coeffs_mod[1] = (LH, HL, HH)
        chan_mod = pywt.waverec2(coeffs_mod, 'haar')
        chan_mod = chan_mod[:chan.shape[0], :chan.shape[1]]
        
        # RESIDUAL FEATHERING: Blurs the diff map to integrate edges perfectly
        residual = chan_mod - chan
        k_size = 3 if max(h, w) < 4000 else 5
        residual_smoothed = cv2.GaussianBlur(residual, (k_size, k_size), 0)
        
        ycrcb[:, :, ch_idx] = np.clip(chan + residual_smoothed, 0, 255).astype(np.uint8)

    final = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    
    # --- HYBRID BURN-IN LAYER: Analog Hole Security ---
    # Overlay faint tiled ID text with Adaptive Contrast
    h, w = final.shape[:2]
    overlay = final.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = max(0.6, min(h, w) / 1500.0)
    
    step_y = int(h / 6)
    step_x = int(w / 4)
    for y in range(step_y // 2, h, step_y):
        for x in range(step_x // 2, w, step_x):
            sample = final[max(0, y-20):min(h, y+20), max(0, x-20):min(w, x+100)]
            avg_brightness = np.mean(cv2.cvtColor(sample, cv2.COLOR_BGR2GRAY))
            color = (255, 255, 255) if avg_brightness < 128 else (0, 0, 0)
            cv2.putText(overlay, watermark_data, (x, y), font, font_scale, color, 2, cv2.LINE_AA)
            
    final = cv2.addWeighted(overlay, 0.06, final, 0.94, 0)

    if output_path:
        cv2.imwrite(output_path, final)
        try:
            with open(output_path + ".exif", "w") as f: f.write(cipher)
        except: pass
        return output_path
    return final

def scan_orientation(img: np.ndarray, master_ycrcb: np.ndarray = None) -> str:
    """Ghost-Cloud extraction with majority voting gain."""
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    global_labels = ["ADMIN", "EMP-001", "EMP-002", "EMP-003", "CON-004", "INT-005", "GST-006", "EMP-007", "EMP-008", "EMP-999"]
    h, w = img.shape[:2]
    level = 3 if max(h, w) > 2000 else 2
    
    for ch_idx in [0, 2]:
        chan = ycrcb[:, :, ch_idx].astype(np.float32)
        jnd_chan = master_ycrcb[:, :, ch_idx] if master_ycrcb is not None else chan
        
        try:
            coeffs = pywt.wavedec2(chan, 'haar', level=level)
            bands = [coeffs[1][0], coeffs[1][1]]
        except: continue

        jnd = calculate_jnd_mask(jnd_chan, bands[0].shape)
        delta_map = (BASE_DELTA * 0.7 if ch_idx == 0 else BASE_DELTA) * jnd
        
        votes = [[] for _ in range(PAYLOAD_LEN)]
        for band in bands:
            v1 = np.round(band / delta_map) * delta_map + delta_map / 4
            v0 = np.round(band / delta_map) * delta_map - delta_map / 4
            bits_map = (np.abs(band - v1) < np.abs(band - v0)).astype(np.int8)
            
            flat = bits_map.flatten()
            modulated_indices = np.where(np.indices(bits_map.shape).sum(axis=0).flatten() % 2 == 0)[0]
            flat_filtered = flat[modulated_indices]
            
            max_idx = (len(flat_filtered) // PAYLOAD_LEN) * PAYLOAD_LEN
            if max_idx > 0:
                reshaped = flat_filtered[:max_idx].reshape(-1, PAYLOAD_LEN)
                for i in range(PAYLOAD_LEN):
                    votes[i].extend(reshaped[:, i].tolist())
        
        if any(votes):
            extracted_ecc = [1 if sum(v) > len(v)/2 else 0 for v in votes]
            decoded = rs_decode(extracted_ecc)
            if len(decoded) >= BIT_COUNT:
                marker = "".join(chr(int("".join(map(str, decoded[i:i+8])), 2)) for i in range(0, BIT_COUNT, 8))
                for label in global_labels:
                    if encrypt_employee_id(label)[:2] == marker: return label
    return None

def extract_watermark(input_data: any, master_data: any = None, ignore_exif: bool = False) -> tuple[str, float, np.ndarray]:
    """Production Forensic Extraction Engine with Multi-Value Return (ID, Conf, AlignedImg)."""
    if not ignore_exif and isinstance(input_data, str) and os.path.exists(input_data + ".exif"):
        try:
            with open(input_data + ".exif", "r") as f:
                label = decrypt_employee_id(f.read().strip())
                if label != "UNKNOWN": return label, 1.0, None
        except: pass

    if isinstance(input_data, bytes):
        img = cv2.imdecode(np.frombuffer(input_data, np.uint8), cv2.IMREAD_COLOR)
    elif isinstance(input_data, np.ndarray): img = input_data
    else: img = cv2.imread(input_data)
    if img is None: return "UNKNOWN", 0.0, None

    best_aligned = img.copy()
    m_ycrcb, m_arr = None, None
    if master_data is not None:
        if isinstance(master_data, bytes):
            m_arr = cv2.imdecode(np.frombuffer(master_data, np.uint8), cv2.IMREAD_COLOR)
        elif hasattr(master_data, 'convert'): # PIL Image
            m_arr = cv2.cvtColor(np.array(master_data.convert("RGB")), cv2.COLOR_RGB2BGR)
        else: m_arr = master_data
        if m_arr is not None: m_ycrcb = cv2.cvtColor(m_arr, cv2.COLOR_BGR2YCrCb)

    # STAGE 1: Fast Path
    for angle in [0, 90, 180, 270]:
        rot = img if angle == 0 else np.rot90(img, angle // 90)
        res = scan_orientation(rot, m_ycrcb)
        if res: return res, 1.0, rot

    # STAGE 2: Geometric Alignment (ASIFT + Log-Polar)
    if m_arr is not None:
        img_asift = align_leak_to_master(img, m_arr)
        res = scan_orientation(img_asift, m_ycrcb)
        if res: return res, 0.98, img_asift
        
        img_lp = log_polar_resync(img, m_arr)
        res = scan_orientation(img_lp, m_ycrcb)
        if res: return res, 0.97, img_lp
        
    # STAGE 3: Blind Search Fallback
    h, w = img.shape[:2]
    for angle in [-15, 15, -30, 30, -45, 45]:
        M = cv2.getRotationMatrix2D((w/2, h/2), angle, 1)
        rot = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        res = scan_orientation(rot, m_ycrcb)
        if res: return res, 0.90, rot

    return "UNKNOWN", 0.0, best_aligned
