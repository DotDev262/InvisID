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

# --- Configuration Constants (OPTIMIZED ROBUST PREMIUM) ---
BIT_COUNT = 16
RS_ECC_BYTES = 32
rs = RSCodec(RS_ECC_BYTES)
BASE_DELTA = 50.0  # Higher for JPEG robustness
PAYLOAD_LEN = BIT_COUNT + RS_ECC_BYTES * 8

DEFAULT_VALID_LABELS = ["ADMIN", "EMP-001", "EMP-002", "EMP-003", "CON-004", "INT-005", "GST-006", "EMP-007", "EMP-008", "EMP-999"]

# Pre-computed encrypted labels for speed
_cached_encrypted_labels = {}
_cached_payloads = {}
BURNIN_ALPHA = 0.0 # Temporarily disabled visible watermark

# --- MATHEMATICAL ENGINE ---

def calculate_jnd_mask(channel: np.ndarray, target_shape: tuple) -> np.ndarray:
    gx = cv2.Sobel(channel, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(channel, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    norm_mag = mag / (np.max(mag) + 1e-5)
    mask = cv2.resize(np.power(norm_mag, 0.8), (target_shape[1], target_shape[0]), interpolation=cv2.INTER_AREA)
    return 0.5 + mask * 2.0 # Slightly higher floor for robustness

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

# --- CRYPTO (AES-GCM for authenticity and pattern hiding) ---

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

def _get_encrypted_label(label: str) -> str:
    if label not in _cached_encrypted_labels:
        key = settings.MASTER_SECRET.encode()[:32].ljust(32, b'\0')
        iv = get_random_bytes(12)  # GCM recommended IV size
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        ciphertext, tag = cipher.encrypt_and_digest(pad(label.encode(), 16))
        # Store: IV (12) + Tag (16) + Ciphertext
        _cached_encrypted_labels[label] = base64.b64encode(iv + tag + ciphertext).decode()
    return _cached_encrypted_labels[label]

def _get_payload_bits(label: str) -> list:
    if label not in _cached_payloads:
        enc_id = _get_encrypted_label(label)
        _cached_payloads[label] = [int(b) for b in "".join(format(ord(c), "08b") for c in enc_id[:2])]
    return _cached_payloads[label]

def encrypt_employee_id(emp_id: str) -> str:
    return _get_encrypted_label(emp_id)

def decrypt_employee_id(cipher_text: str) -> Optional[str]:
    try:
        key = settings.MASTER_SECRET.encode()[:32].ljust(32, b'\0')
        data = base64.b64decode(cipher_text)
        iv = data[:12]
        tag = data[12:28]
        ciphertext = data[28:]
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        return unpad(cipher.decrypt_and_verify(ciphertext, tag), 16).decode()
    except: return None

# --- CRYPTO (AES-GCM for authenticity and pattern hiding) ---

# --- ASIFT (Affine-SIFT for rotation robustness) ---
def affine_skew(tilt, phi, img, mask=None):
    '''Apply affine transformation to simulate different viewing angles'''
    h, w = img.shape[:2]
    if mask is None:
        mask = np.zeros((h, w), np.uint8)
        mask[:] = 255
    A = np.float32([[1, 0, 0], [0, 1, 0]])
    if phi != 0.0:
        phi = np.deg2rad(phi)
        s, c = np.sin(phi), np.cos(phi)
        A = np.float32([[c,-s], [ s, c]])
        corners = [[0, 0], [w, 0], [w, h], [0, h]]
        tcorners = np.int32(np.dot(corners, A.T))
        x, y, w, h = cv2.boundingRect(tcorners.reshape(1,-1,2))
        A = np.hstack([A, [[-x], [-y]]])
        img = cv2.warpAffine(img, A, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    if tilt != 1.0:
        s = 0.8*np.sqrt(tilt*tilt-1)
        img = cv2.GaussianBlur(img, (0, 0), sigmaX=s, sigmaY=0.01)
        img = cv2.resize(img, (0, 0), fx=1.0/tilt, fy=1.0, interpolation=cv2.INTER_NEAREST)
        A[0] /= tilt
    if phi != 0.0 or tilt != 1.0:
        h, w = img.shape[:2]
        mask = cv2.warpAffine(mask, A, (w, h), flags=cv2.INTER_NEAREST)
    Ai = cv2.invertAffineTransform(A)
    return img, mask, Ai


def affine_detect(detector, img, mask=None):
    '''Apply affine transformations and detect keypoints'''
    params = [(1.0, 0.0)]
    for t in 2**(0.5*np.arange(1,4)):  # Reduced for speed
        for phi in np.arange(0, 180, 72.0 / t):
            params.append((t, phi))
    
    keypoints, descrs = [], []
    for t, phi in params:
        timg, tmask, Ai = affine_skew(t, phi, img)
        kps, des = detector.detectAndCompute(timg, tmask)
        for kp in kps:
            x, y = kp.pt
            kp.pt = tuple(np.dot(Ai, (x, y, 1)))
        keypoints.extend(kps)
        if des is not None:
            descrs.extend(des)
    return keypoints, np.array(descrs) if descrs else np.array([])


def align_leak_asift(leak_img: np.ndarray, master_img: np.ndarray) -> Optional[np.ndarray]:
    '''ASIFT-based alignment for full rotation invariance'''
    try:
        h_o, w_o = master_img.shape[:2]
        s_c = 1000.0 / max(h_o, w_o)
        m_c = cv2.resize(cv2.cvtColor(master_img, cv2.COLOR_BGR2GRAY), (int(w_o*s_c), int(h_o*s_c)))
        l_c = cv2.resize(cv2.cvtColor(leak_img, cv2.COLOR_BGR2GRAY), (int(w_o*s_c), int(h_o*s_c)))
        
        sift = cv2.SIFT_create(5000)
        kp1, des1 = affine_detect(sift, m_c)
        kp2, des2 = affine_detect(sift, l_c)
        
        if len(kp1) < 10 or len(kp2) < 10:
            return None
            
        matcher = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))
        matches = matcher.knnMatch(des2, des1, k=2)
        good = [m for m, n in matches if m.distance < 0.7 * n.distance]
        
        if len(good) < 10:
            return None
            
        src_pts = np.float32([kp2[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp1[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        
        M, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
        if M is None:
            return None
            
        return cv2.warpPerspective(leak_img, M, (w_o, h_o), borderMode=cv2.BORDER_REPLICATE)
    except:
        return None

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
        sift_f = cv2.SIFT_create(5000)  # Reduced from 25000 for speed
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

    # Generate payloads (using cached functions)
    enc_id = _get_encrypted_label(watermark_data)
    payload_bits = _get_payload_bits(watermark_data)
    payload = np.array(rs_encode(payload_bits))
    
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    h, w = img.shape[:2]
    
    # 1. DWT-QIM Layer (Premium Quality)
    wavelet = 'db4'
    for ch_idx in [0, 1, 2]:
        chan = ycrcb[:, :, ch_idx].astype(np.float32)
        coeffs = pywt.wavedec2(chan, wavelet, level=4)
        for level in [3, 4]:
            if ch_idx == 0 and level < 4: continue  # Y channel: only level 4
            if level == 4: target_bands = [coeffs[1][0], coeffs[1][1]]
            elif level == 3: target_bands = [coeffs[2][0], coeffs[2][1]]
            elif level == 2: target_bands = [coeffs[3][0], coeffs[3][1]]
            for band_idx, band in enumerate(target_bands):
                jnd = calculate_jnd_mask(chan, band.shape)
                scale = 2.5 if level == 4 else (1.6 if level == 3 else 0.9)
                d_map = BASE_DELTA * scale * jnd
                payload_map = np.tile(payload, (band.size // PAYLOAD_LEN) + 1)[:band.size].reshape(band.shape)
                if level == 4: coeffs[1] = list(coeffs[1]); coeffs[1][band_idx] = qim_mod(band, payload_map, d_map); coeffs[1] = tuple(coeffs[1])
                elif level == 3: coeffs[2] = list(coeffs[2]); coeffs[2][band_idx] = qim_mod(band, payload_map, d_map); coeffs[2] = tuple(coeffs[2])
                elif level == 2: coeffs[3] = list(coeffs[3]); coeffs[3][band_idx] = qim_mod(band, payload_map, d_map); coeffs[3] = tuple(coeffs[3])
        chan_mod = pywt.waverec2(coeffs, wavelet)[:h, :w]
        wm_signal = cv2.GaussianBlur(chan_mod - chan, (3, 3), 0.5)
        alpha = 0.30 if ch_idx == 0 else 0.7  # Balanced
        ycrcb[:, :, ch_idx] = np.clip(chan + wm_signal * alpha, 0, 255).astype(np.uint8)

    # 2. Spatial Spread Spectrum Layer - Very low for quality
    import hashlib
    seed = int(hashlib.sha256(enc_id.encode()).hexdigest(), 16) % (2**32)
    np.random.seed(seed)
    prn = np.random.normal(0, 1, (h, w)).astype(np.float32)
    spatial_signal = (prn * 0.20).astype(np.float32)  # Balanced for quality
    ycrcb[:, :, 0] = np.clip(ycrcb[:, :, 0].astype(np.float32) + spatial_signal, 0, 255).astype(np.uint8)

    final = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    if output_path:
        cv2.imwrite(output_path, final, [cv2.IMWRITE_PNG_COMPRESSION, 0])
        with open(output_path + ".exif", "w") as f: f.write(encrypt_employee_id(watermark_data))
        return output_path
    return final

def scan_orientation(img: np.ndarray, master_ycrcb: Optional[np.ndarray] = None, valid_labels: Optional[list[str]] = None) -> Optional[str]:
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb); labels = valid_labels or DEFAULT_VALID_LABELS
    wavelet = 'db4'
    results = []
    
    # --- Layer 1: DWT-QIM Voting ---
    for ch_idx in [0, 1, 2]:
        chan = ycrcb[:, :, ch_idx].astype(np.float32); jnd_c = master_ycrcb[:,:,ch_idx] if master_ycrcb is not None else chan
        try:
            coeffs = pywt.wavedec2(chan, wavelet, level=4)
            bands = [(coeffs[1][0], 4), (coeffs[1][1], 4), (coeffs[2][0], 3), (coeffs[2][1], 3)]
        except: continue
        votes = [[] for _ in range(PAYLOAD_LEN)]
        for band, level in bands:
            if ch_idx == 0 and level < 4: continue
            jnd = calculate_jnd_mask(jnd_c, band.shape)
            scale = 2.5 if level == 4 else 1.6
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
                    if _get_encrypted_label(label)[:2] == m: results.append(label)

    if results:
        from collections import Counter
        counts = Counter(results).most_common(1)
        # Fix 1: Relaxed consensus. If only one channel detected something (e.g. Grayscale), accept it.
        # If multiple channels found data, require at least 2 to agree.
        if len(results) == 1 or counts[0][1] >= 2:
            return counts[0][0]
        # If results exist but no consensus, we continue to spatial layer as fallback

    # --- Layer 2: Fast Spatial Backstop (Optimized) ---
    y_chan = ycrcb[:, :, 0].astype(np.float32)
    best_overall_corr = -1.0
    best_overall_label = None
    
    # Reduced scales [1.0, 0.5] for speed - covers most cases
    for s_factor in [1.0, 0.5]:
        h_s, w_s = int(ycrcb.shape[0] * s_factor), int(ycrcb.shape[1] * s_factor)
        if h_s < 100 or w_s < 100: continue
        
        y_s = cv2.resize(y_chan, (w_s, h_s))
        y_noise = cv2.Laplacian(y_s, cv2.CV_32F)
        
        for label in labels:
            enc_id = _get_encrypted_label(label)
            import hashlib
            seed = int(hashlib.sha256(enc_id.encode()).hexdigest(), 16) % (2**32)
            np.random.seed(seed)
            prn = np.random.normal(0, 1, (h_s, w_s)).astype(np.float32)
            corr = np.sum(y_noise * prn) / (np.linalg.norm(y_noise) * np.linalg.norm(prn) + 1e-9)
            if corr > best_overall_corr:
                best_overall_corr = corr
                best_overall_label = label
            
    if best_overall_corr > 0.008:
        return best_overall_label

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
    # Optimized extraction with fewer rotations for speed
    ROTATIONS = [0, 90, 180, 270]
    
    # Try WITHOUT alignment first (sometimes alignment destroys watermark)
    for a in ROTATIONS:
        rot = rotate_image(img, a) if a != 0 else img
        res = scan_orientation(rot, m_ycrcb, valid_labels)
        if res: return res, 1.0, rot
    
    # Try alignment as fallback
    if m_arr is not None:
        img_a = align_leak_to_master(img, m_arr)
        if img_a is not None:
            for a in ROTATIONS:
                rot = rotate_image(img_a, a) if a != 0 else img_a
                res = scan_orientation(rot, m_ycrcb, valid_labels)
                if res: return res, 0.98, rot
        
        img_l = log_polar_resync(img, m_arr)
        if img_l is not None:
            for a in ROTATIONS:
                rot = rotate_image(img_l, a) if a != 0 else img_l
                res = scan_orientation(rot, m_ycrcb, valid_labels)
                if res: return res, 0.97, rot
        
        # Try ASIFT alignment for full rotation invariance
        img_asift = align_leak_asift(img, m_arr)
        if img_asift is not None:
            for a in ROTATIONS:
                rot = rotate_image(img_asift, a) if a != 0 else img_asift
                res = scan_orientation(rot, m_ycrcb, valid_labels)
                if res: return res, 0.96, rot
    
    # Multi-Scale Recovery (improved for scaling attacks)
    h_orig, w_orig = img.shape[:2]
    for scale in [1.0, 0.75, 0.5, 0.35, 0.25]:
        if scale != 1.0:
            img_scaled = cv2.resize(img, (int(w_orig * scale), int(h_orig * scale)))
            m_ycrcb_scaled = cv2.resize(m_ycrcb, (int(w_orig * scale), int(h_orig * scale))) if m_ycrcb is not None else None
        else:
            img_scaled = img
            m_ycrcb_scaled = m_ycrcb
        
        # Try extraction at this scale
        for a in ROTATIONS:
            rot = rotate_image(img_scaled, a) if a != 0 else img_scaled
            res = scan_orientation(rot, m_ycrcb_scaled, valid_labels)
            if res: return res, 1.0 * scale, rot
        
        # Try alignment at this scale
        if m_arr is not None and scale < 1.0:
            m_arr_scaled = cv2.resize(m_arr, (int(w_orig * scale), int(h_orig * scale)))
            img_aligned = align_leak_to_master(img_scaled, m_arr_scaled)
            if img_aligned is not None:
                for a in ROTATIONS:
                    rot = rotate_image(img_aligned, a) if a != 0 else img_aligned
                    res = scan_orientation(rot, m_ycrcb_scaled, valid_labels)
                    if res: return res, 0.95 * scale, rot
            
                # Also try without master
                res = scan_orientation(img_aligned, None, valid_labels)
                if res: return res, 0.95 * scale, img_aligned
            
    return None, 0.0, img.copy()
