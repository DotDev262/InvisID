# InvisID: Forensic Leak Attribution System

[![Security: STRIDE](https://img.shields.io/badge/Security-STRIDE-blue)](./SECURITY_REPORT.md)
[![Status: Technical Validation](https://img.shields.io/badge/Status-Validation_Phase-orange)](./EXECUTION_PLAN.md)
[![Accuracy: 96.2% (Preliminary)](https://img.shields.io/badge/Preliminary_Accuracy-96.2%25-brightgreen)](./scripts/forensic_ultimate_test.py)

**InvisID** is an elite forensic platform designed for high-confidence leak attribution. By combining **True ASIFT** alignment with a **JND-Guided DWT-QIM** architecture, InvisID ensures that sensitive digital assets can be traced back to their source even after extreme geometric distortion, lossy compression, or 8K resolution interpolation.

## 🛡️ "Smart" Defense-in-Depth Architecture

InvisID implements a multi-layered security posture to ensure both forensic integrity and system protection:

- **True ASIFT Alignment**: A multi-scale alignment engine that simulates multiple camera optical axes to perfectly resynchronize 8K assets after 3D perspective skew.
- **JND-Guided DWT-QIM**: Texture-aware frequency domain embedding that scales strength based on local complexity—ensuring absolute invisibility in smooth regions and extreme robustness in textured areas.
- **Encryption at Rest (AES-256-GCM)**: All master assets are stored using authenticated encryption to prevent unauthorized disk access or tampering.
- **HMAC Request Signing**: Every UI transaction is cryptographically signed using HMAC-SHA256 to eliminate Man-in-the-Middle (MITM) and Replay attacks.
- **Reed-Solomon RS Armor**: Forensic identities are protected by high-capacity Error Correction Codes to recover data from noisy or corrupted extractions.
- **Session Heartbeat**: Real-time server instance tracking via unique IDs to enforce immediate security logout upon system restart.

## 🚀 Elite Forensic Features

- **High-Fidelity PDF Reports**: Professional forensic case export including ASIFT alignment proofs and visual evidence.
- **Stress-Test Lab 4.0**: Advanced adversarial simulation suite including **WhatsApp Simulation**, **3D Perspective Tilt**, and **Median Filtering**.
- **8K Resolution Support**: Fully vectorized NumPy-based engine capable of processing 33-megapixel images with zero performance degradation.

## 🛠️ Validation & Forensic Audit

```bash
# Install dependencies
uv sync

# Setup environment
cp .env.template .env # Configure your MASTER_SECRET

# Start Development Server
uv run app/main.py

# Run Technical Forensic Audit (Preliminary Benchmark)
PYTHONPATH=. uv run scripts/forensic_ultimate_test.py
```

---
**Academic Disclaimer**: This project is a Cybersecurity Capstone currently in the **Active Technical Validation** phase. Current benchmarks are subject to further stress-testing.
