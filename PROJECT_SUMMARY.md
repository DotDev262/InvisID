# InvisID: Technical Deep Dive & System Architecture

InvisID is a high-assurance image leak attribution and forensic system. It is designed to protect sensitive visual assets by embedding robust, invisible, and cryptographically secure watermarks, while maintaining a tamper-evident audit trail of every interaction.

## 1. Core Mission & Problem Statement
The "Analog Hole" (taking a photo of a screen) is the primary vector for leaking sensitive imagery. InvisID solves this by:
- **Embedding**: Inserting an invisible ID that survives screen capture, cropping, and compression.
- **Alignment**: Using computer vision to "undo" geometric distortions in leaked photos.
- **Verification**: Providing a cryptographically signed proof of the leaker's identity.

---

## 2. System Architecture

### **Backend (FastAPI)**
- **Framework**: High-performance asynchronous Python (FastAPI).
- **Task Management**: Uses `BackgroundTasks` for heavy lifting like image encryption, watermark embedding, and forensic alignment.
- **Dependency Management**: Optimized with `uv` for lightning-fast builds and reproducible environments.
- **Instance Tracking**: Generates a unique `X-Instance-ID` on startup to track server lifecycles and session validity.

### **Security Middleware**
- **Rate Limiting**: Protects sensitive endpoints (Login, Download, Investigate).
- **Hardened Headers**:
    - **HSTS**: Forces HTTPS for a year (`max-age=31536000`).
    - **CSP**: Strict Content Security Policy preventing unauthorized script execution or canvas data extraction.
    - **COEP/CORP**: Cross-Origin isolation to prevent "side-channel" pixel reading by browser extensions.
    - **X-Robots-Tag**: `noindex, nofollow` to prevent accidental search engine indexing.

---

## 3. The Watermarking Engine (`image_service.py`)

InvisID uses a multi-layered approach to steganography:

### **Embedding Strategy: Multi-scale DWT-QIM**
1.  **Color Space**: Processes images in **YCrCb** (Y-channel) to minimize visual artifacts.
2.  **Transform**: Applies **Discrete Wavelet Transform (DWT)** (using `db4` wavelets for smoothness) to identify stable frequency bands.
3.  **Modulation**: Uses **Quantization Index Modulation (QIM)** to embed bits into wavelet coefficients. This is significantly more robust to noise than Least Significant Bit (LSB) methods.
4.  **Smoothing**: Applies a light Gaussian blur to the watermark signal to eliminate "grit" or visual noise in smooth areas of the image.

### **Robustness & Security**
- **Error Correction**: Implements **Reed-Solomon (RS)** encoding. Even if 20-30% of the watermark signal is destroyed by compression or noise, the ID remains recoverable.
- **Payload Encryption**: The embedded ID is not stored in plain text. It is **AES-GCM encrypted** using a Master Secret. An unauthorized party cannot even "read" the ID if they managed to extract it.
- **Spread Spectrum**: Adds a spatial spread spectrum layer as a secondary, "backup" detection signal.

---

## 4. Forensic Investigation & Alignment

To identify a leak from a low-quality photo (the "Analog Hole"), InvisID performs:

### **Geometric Resynchronization (ASIFT)**
- Uses **Affine SIFT (ASIFT)** to detect keypoints and calculate the perspective transformation between the leak and the original master.
- **Log-Polar Mapping**: Used to handle extreme rotation and scaling that standard SIFT might miss.
- **Alignment Engine**: The system "warps" the leaked photo back into the coordinate space of the original master before attempting extraction.

### **Voting & Consensus**
- The extraction engine doesn't just try once. It scans multiple orientations, scales, and wavelet levels.
- A **Voting Algorithm** aggregates results across these scales to provide a final **Confidence Score**.

---

## 5. Security & Data Integrity

### **Encrypted Storage at Rest**
- Master images are never stored as raw files. They are encrypted via **AES-GCM** immediately upon upload.
- File paths are randomized (UUIDs) to prevent predictable URL attacks.

### **Cryptographically Chained Audit Logs**
- **Blockchain Integrity**: Each log entry contains a `current_hash`, which is an **HMAC-SHA256** of (`timestamp` + `user_id` + `event` + `previous_hash`).
- **Tamper Evidence**: If an admin or attacker deletes a row or modifies a log entry, the hash chain breaks, making the tampering immediately evident.

### **Client-Side Data Loss Prevention (DLP)**
- **DevTools Detection**: A specialized heuristic monitors window resize events (300px+ threshold with 500ms debounce) to detect if a user opens the browser's inspection tools.
- **Anti-Capture Shield**: A focus-based security shield that obscures the UI if the window loses focus or if suspicious resizing is detected.
- **Grace Periods**: Provides a 3-second grace period (`isDownloading`) for legitimate file-save dialogs to prevent false positives.
- **Log-Strike**: Automatically reports security violations (right-click, DevTools, screenshots) to the server, identifying the specific `employee_id`.

---

## 6. Database Schema Summary

- **`master_images`**: Metadata for original assets (ID, Encrypted Path, SHA-256 hash, Soft-delete timestamp).
- **`jobs`**: State machine for background tasks (Pending -> Processing -> Completed/Failed).
- **`audit_logs`**: The tamper-proof ledger of all system activity.

---

## 7. Operational Scripts

- `attack_simulator.py`: Stress-tests the watermark against JPEG compression, Gaussian noise, and blurring.
- `analog_hole_test.py`: Simulates the effect of taking a physical photo of a screen.
- `forensic_report_gen`: Automates the creation of PDF evidence reports with side-by-side leak comparisons.
- `clear_db.sh`: Securely wipes the environment for development/re-deployment.
