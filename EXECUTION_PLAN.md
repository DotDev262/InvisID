# InvisID - Final Project Plan
## Leak Attribution System for Sensitive Images

**Version:** Beta (Smart Architecture - Validation Phase)  
**Date:** March 10, 2026  
**Project Type:** Cybersecurity Capstone  
**Status:** PHASE 4: COMPREHENSIVE TECHNICAL VALIDATION (STRESS-TESTING)

---

## 1. Project Overview

### Purpose
InvisID is a **forensic leak attribution system** designed to maintain absolute chain of custody over sensitive digital assets through encrypted invisible watermarking, cryptographic audit trails, and high-precision feature alignment.

### Tech Stack (Finalized)
| Component | Technology | Implementation Detail |
|-----------|------------|-----------------------|
| **Backend** | FastAPI (Python 3.12) | Lifespan-managed background tasks, Security-Headers |
| **Forensics** | **Multi-Scale True ASIFT** | Affine-SIFT with 3D tilt simulation and resolution normalization |
| **Watermarking** | **JND-Guided DWT-QIM** | Texture-aware frequency domain embedding (Y + Cb channels) |
| **Error Correction** | **Reed-Solomon (RS)** | RS-Armor for bit-flip recovery in high-noise leaks |
| **Storage** | SQLite | Full query parameterization & internal PNG conversion |
| **Crypto** | **AES-256-GCM** | Authenticated Encryption at Rest for all master assets |
| **Auth** | **HMAC-SHA256** | Replay-resistant UI signing with Instance Heartbeat |

---

## 2. Architecture & Module Structure
- `app/routers/admin.py`: Dynamic metrics, Master Ingest, Diagnostic Engine.
- `app/routers/investigate.py`: Evidence Management System, PDF Report Engine.
- `app/routers/stress_test.py`: Sequential Multi-Vector simulation suite (Platinum Suite).
- `app/services/image_service.py`: Core forensic algorithms (**ASIFT + DWT-QIM + RS Armor**).
- `scripts/`: Standalone Forensic Audit Suite (Preliminary 96.2% accuracy verification).

---

## 13. Implementation Status (Updated March 10, 2026)

### 🕒 Phase 4: Platinum Tier (VALIDATION IN PROGRESS)
- [ ] **Technical Accuracy Audit**: Preliminary benchmark 96.2% across 13 attack vectors.
- [x] **ASIFT Alignment Engine**: Integrated True Affine-SIFT simulation for 3D tilts.
- [x] **JND Model Integration**: Integrated texture-masking logic for invisibility.
- [x] **Resolution-Adaptive Engine**: NumPy-based 8K support active.
- [x] **Security Hardening**: AES-256-GCM and HMAC-SHA256 pipelines operational.

### 🕒 Phase 5: User Trials & Real-World Validation (PENDING AUDIT)
- [x] **8K High-Res Validation**: Confirmed signal survival on ultra-HD organization assets.
- [ ] **Cross-Device Testing**: Verifying extraction from images shared via mobile apps.
- [ ] **Multi-User Stress**: Simultaneous downloads and investigations.

---

## 15. Security Verification (Ongoing)
The system is being audited against the following threats:
1. **Geometric Attacks**: Mitigated by **True ASIFT** alignment.
2. **Signal Corruption**: Mitigated by **DWT-QIM** patterns and **RS-Armor**.
3. **Asset Tampering**: Mitigated by **AES-256-GCM** authenticated encryption.
4. **Replay Attacks**: Mitigated by **HMAC-SHA256** and Instance Heartbeat.
5. **Log Tampering**: Detectable via cryptographic hash-chaining.

**Document Version:** Beta 4.1 (Validation)  
**Last Updated:** March 10, 2026  
**Status:** UNDERGOING TECHNICAL STRESS-TESTING
