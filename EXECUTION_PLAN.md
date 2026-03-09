# InvisID - Final Project Plan
## Leak Attribution System for Sensitive Images

**Version:** Final (Platinum Tier - High Precision)  
**Date:** March 9, 2026  
**Project Type:** Cybersecurity Capstone  
**Status:** PHASE 5: USER TRIALS & FIELD VALIDATION

---

## 1. Project Overview

### Purpose
InvisID is a **forensic leak attribution system** designed to maintain absolute chain of custody over sensitive digital assets through encrypted invisible watermarking, cryptographic audit trails, and high-precision feature alignment.

### Tech Stack (Finalized)
| Component | Technology | Implementation Detail |
|-----------|------------|-----------------------|
| **Backend** | FastAPI (Python 3.12) | Lifespan-managed background tasks, Security-Headers |
| **Forensics** | **SIFT-based Homography** | High-precision alignment using SIFT + FLANN Matcher |
| **Watermarking** | Differential-Mean | Green-channel redundant embedding (10x redundancy) |
| **Storage** | SQLite | Full query parameterization & internal PNG conversion |
| **Crypto** | AES-256-GCM | Authenticated Encryption at Rest |
| **Auth** | HMAC-SHA256 | Replay-resistant signing with Instance Heartbeat |

---

## 2. Final Architecture & Module Structure
- `app/routers/admin.py`: Dynamic metrics (weekly trends), Master Ingest, Diagnostic Engine.
- `app/routers/investigate.py`: **Evidence Management System**, PDF Report Engine, SIFT-Alignment logic.
- `app/routers/stress_test.py`: Sequential Multi-Vector simulation suite (Intensity-specific).
- `app/services/image_service.py`: Core forensic algorithms (Differential-Mean + SIFT Homography).
- `scripts/`: Standalone Forensic Audit Suite (100% Accuracy verification scripts).

---

## 13. Implementation Status (Updated March 9, 2026)

### ✅ Phase 4: Platinum Tier (Technical Complete)
- [x] **100% Technical Accuracy**: Verified 13/13 attack vectors in automated suite.
- [x] **SIFT Alignment Engine**: Automatic correction of 3D tilt, rotation, and scaling.
- [x] **Formal PDF Reporting**: Professional forensic case export with visual evidence.
- [x] **Dynamic Identity Suite**: 8 distinct forensic identities managed via environment.

### 🕒 Phase 5: User Trials & Real-World Validation (IN PROGRESS)
- [ ] **Cross-Device Testing**: Verifying extraction from images shared via mobile apps.
- [ ] **Multi-User Stress**: Simultaneous downloads and investigations by different team members.
- [ ] **UAT (User Acceptance Testing)**: Collecting feedback on SOC Dashboard usability.
- [ ] **Analog Hole Simulation**: Printing and scanning/re-photographing assets.

---

## 15. Final Security Verification (Technical)
The system has been audited against the following threats:
1. **Geometric Attacks**: Corrected by SIFT-based homography alignment.
2. **Signal Attacks**: Mitigated by block-based differential mean redundancy.
3. **Replay Attacks**: Blocked by HMAC-SHA256 timestamp verification window.
4. **Log Tampering**: Detectable via the cryptographic hash-chain validator.
5. **DDoS/Brute Force**: Mitigated via custom `RateLimitMiddleware`.

**Document Version:** Platinum-Tier Beta  
**Last Updated:** March 9, 2026  
**Status:** UNDERGOING FIELD TRIALS
