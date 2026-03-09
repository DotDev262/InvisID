# InvisID: Forensic Leak Attribution System

[![Security: STRIDE](https://img.shields.io/badge/Security-STRIDE-blue)](./SECURITY_REPORT.md)
[![Status: Beta Trials](https://img.shields.io/badge/Status-User_Trials-orange)](./EXECUTION_PLAN.md)
[![Accuracy: 100% (Technical)](https://img.shields.io/badge/Tech_Accuracy-100%25-brightgreen)](./scripts/forensic_ultimate_test.py)

**InvisID** is an elite forensic platform designed for high-confidence leak attribution. By combining high-precision SIFT-based Homography with differential-mean watermarking, InvisID ensures that sensitive digital assets can be traced back to their source even after extreme geometric distortion, compression, or system compromise.

## 🛡️ "Platinum-Tier" Security Architecture

Developed as a premier Cybersecurity Capstone, InvisID implements absolute **Defense-in-Depth**:

- **SIFT-based Homography Alignment**: Automatically corrects 3D perspective tilts, rotations, and scaling by aligning leaks against master assets.
- **Cryptographic Log Chaining**: Audit logs are mathematically linked using SHA-256 hashes (Blockchain-style), making them tamper-evident.
- **Encryption at Rest (AES-256-GCM)**: All master images are encrypted before being written to disk using authenticated encryption.
- **HMAC Request Signing**: Every UI request is cryptographically signed to eliminate Man-in-the-Middle (MITM) and Replay attacks.
- **Session Heartbeat**: Real-time detection of server restarts via unique process instance IDs to enforce immediate security logout.

## 🚀 Elite Forensic Features

- **High-Fidelity PDF Reports**: Generate professional forensic reports including executive summaries, technical validation, and visual evidence.
- **Dynamic SOC Dashboard**: Real-time Security Operations Center view with live metrics, weekly trend analysis, and a live activity feed.
- **Stress-Test Lab 3.0**: Advanced adversarial simulation suite with 100% verified resilience across 13+ attack vectors.
- **Forensic Report Archive**: Persistent database of all leak identification tasks with instant report recall and visual evidence preservation.

## 🛠️ Installation & Beta Testing

```bash
# Install dependencies
uv sync

# Setup environment
cp .env.template .env # Configure your MASTER_SECRET and API keys

# Start Server
uv run app/main.py

# Run Technical Forensic Audit
PYTHONPATH=. uv run scripts/forensic_ultimate_test.py
```

## 📖 Evaluation Documentation
- [Execution Plan](./EXECUTION_PLAN.md): Technical roadmap and **User Trial Status**.
- [Security Report](./SECURITY_REPORT.md): Deep-dive into **STRIDE**, **SIFT Alignment**, and **Forensic Robustness**.

---
**Academic Disclaimer**: This project is a Cybersecurity Capstone currently in the **User Trial & Field Validation** phase.
