# InvisID - Final Project Plan
## Leak Attribution System for Sensitive Images

**Version:** Final  
**Date:** February 2026  
**Project Type:** Cybersecurity Capstone  
**Team:** 4 Computer Science Students (3rd Year)  
**Timeline:** 8 Weeks  

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [The Problem & Solution](#2-the-problem--solution)
3. [Technical Architecture](#3-technical-architecture)
4. [Core Workflows](#4-core-workflows)
5. [API Endpoints](#5-api-endpoints)
6. [Module Structure](#6-module-structure)
7. [Security (SSDLC + STRIDE)](#7-security-ssdlc--stride)
8. [Timeline](#8-timeline)
9. [Dependencies](#9-dependencies)
10. [Deliverables](#10-deliverables)
11. [Optional Enhancement: RivaGAN Retraining](#11-optional-enhancement-rivagan-retraining)
12. [Summary](#12-summary)
13. [Current Status & Implementation Details (March 2026)](#13-current-status--implementation-details-march-2026)
14. [Future Enhancements & Post-MVP Roadmap](#14-future-enhancements--post-mvp-roadmap)

---

## 1. Project Overview

### Purpose

InvisID is a **leak attribution system** that traces leaked sensitive images back to the source employee using invisible watermarking.

### Use Case

1. Company has sensitive product designs (internal documents, prototypes, confidential images)
2. Employees request to download these images
3. System invisibly embeds their unique Employee ID into the image at download time
4. If that image later leaks to the press or appears online
5. Admin uploads the leaked image → System extracts watermark → Identifies which employee shared it
6. Cross-reference with audit logs to confirm chain of custody

### Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python 3.12) |
| Watermarking | `invisible-watermark` (DWT-DCT-SVD) |
| Image Processing | `Pillow` (Sanitization & EXIF Stripping) |
| File Inspection | `python-magic` (Deep MIME Verification) |
| Encryption | AES-256-GCM (PyCryptodome) |
| Linting/Security | `Ruff` (S, B, C90 rules) |
| Security Scanning | `Bandit` (SAST), `pip-audit` (SCA) |
| Quality Gate | `SonarQube` / `SonarCloud` |
| Package Manager | `UV` |

### Scope & Limitations

#### In Scope (What We Solve)
- **Digital Data Exfiltration**: Unauthorized file sharing, email attachments, USB transfers, cloud uploads
- **JPEG/PNG Compression Attacks**: Quality 50 and above
- **Gaussian Noise**: Moderate levels (σ ≤ 0.05)
- **Basic Image Filtering**: Blur, brightness, contrast adjustments
- **Accidental Sharing**: Employee sends file to friend or posts to social media
- **Casual Leak Detection**: Most common insider threat scenarios

#### Out of Scope (Explicitly Not Solved)
- **Analog Hole Attacks**: Photographing a screen with a smartphone
- **Screen Capture**: Taking a screenshot of the watermarked image (OS-level capture)
- **Severe Geometric Cropping**: >30% content removal
- **Print-Scan Attacks**: Physical printing and re-scanning
- **Adversarial Removal**: AI-based watermark removal tools
- **Recording Attacks**: Screen recording software (OBS, etc.)

---

## 2. The Problem & Solution

### The Problem

> Your company shares sensitive product designs, internal documents, or confidential images with employees. If one of these images leaks to the press or competitors, how do you find the source?

### The Solution: InvisID

InvisID traces leaks by embedding a unique, encrypted Employee ID into images **at the moment an employee downloads them**. If that image later surfaces externally, scan it to decode the watermark and identify the leaker.

### How It Works

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  1. ADMIN UPLOADS                                                            │
│     Company uploads sensitive product design images                          │
│                                                                              │
│  2. EMPLOYEE DOWNLOADS                                                       │
│     Employee requests to download image                                      │
│     ↓                                                                        │
│     System invisibly embeds their unique Employee ID                         │
│     ↓                                                                        │
│     Employee receives watermarked image                                      │
│                                                                              │
│  3. IMAGE LEAKS                                                              │
│     Leaked image found on social media/press                                 │
│                                                                              │
│  4. TRACE SOURCE                                                             │
│     Admin uploads leaked image → System extracts ID → Identifies leaker      │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Technical Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                    INVISID SYSTEM                                       │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                              CLIENTS
                    ┌──────────────────┐                      ┌──────────────────┐
                    │   Admin Browser  │                      │ Employee Browser │
                    │   (Security)     │                      │    (Download)    │
                    └────────┬─────────┘                      └────────┬─────────┘
                             │                                         │
                             │ HTTP + API Key                          │ HTTP + API Key
                             ▼                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              FASTAPI BACKEND                                            │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                           SECURITY LAYER                                        │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐     │    │
│  │  │ API Key     │  │ Rate        │  │ Input       │  │ Security Headers    │     │    │
│  │  │ Auth        │  │ Limiter     │  │ Validator   │  │ Middleware          │     │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘     │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐    │
│  │                           CORE MODULES                                          │    │
│  │                                                                                 │    │
│  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐      │    │
│  │  │ Admin        │   │ Download     │   │ Reveal       │   │ Attack       │      │    │
│  │  │ Router       │   │ Router       │   │ Router       │   │ Router       │      │    │
│  │  │              │   │ (Embed)      │   │              │   │              │      │    │
│  │  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘      │    │
│  │         │                  │                  │                  │              │    │
│  │         └──────────────────┴─────────┬────────┴──────────────────┘              │    │
│  │                                      │                                          │    │
│  │                                      ▼                                          │    │
│  │  ┌───────────────────────────────────────────────────────────────────────┐      │    │
│  │  │                         SERVICE LAYER                                 │      │    │
│  │  │                                                                       │      │    │
│  │  │  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐               │      │    │
│  │  │  │ Auth Service │   │ Image Service│   │ Audit Service│               │      │    │
│  │  │  └──────────────┘   └──────────────┘   └──────────────┘               │      │    │
│  │  │                                                                       │      │    │
│  │  └───────────────────────────────────────────────────────────────────────┘      │    │
│  └─────────────────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA LAYER                                                 │
│                                                                                         │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐                        │
│  │  Master Images  │   │   Audit Logs    │   │   Config        │                        │
│  │  (storage/)     │   │  (logs.json)    │   │   (.env)        │                        │
│  └─────────────────┘   └─────────────────┘   └─────────────────┘                        │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Employee requests download
        │
        ▼
Auth verifies API key
        │
        ▼
Get employee ID from API key (EMP-007)
        │
        ▼
AES-256-GCM Encryption (encrypts EMP-007)
        │
        ▼
DWT+DCT Steganography (embeds encrypted ID into image)
        │
        ▼
Employee receives watermarked image
        │
        ▼
AUDIT LOG: "EMP-007 downloaded design_v2.png at 2026-02-22 10:30:00"
```

---

## 4. Core Workflows

### Workflow 1: Admin Uploads Master Image

```
Admin uploads image
        │
        ▼
API validates (size, type)
        │
        ▼
Save to /storage/master
        │
        ▼
AUDIT LOG: "admin uploaded design_v1.png at 2026-02-22 10:30:00"
```

### Workflow 2: Employee Downloads Image (Auto-Embed)

```
Employee requests download
        │
        ▼
Auth verifies employee API key
        │
        ▼
Identify employee (EMP-007)
        │
        ▼
Get master image from storage
        │
        ▼
Crypto: Encrypt EMP-007 → encrypted_data
        │
        ▼
Stego: Embed encrypted_data into image
        │
        ▼
Employee receives watermarked image
        │
        ▼
AUDIT LOG: "EMP-007 downloaded design_v2.png at 2026-02-22 10:35:00"
```

### Workflow 3: Investigate a Leak

```
Admin uploads leaked image
        │
        ▼
Stego: Extract watermark
        │
        ▼
Crypto: Decrypt → Employee ID
        │
        ▼
Return: "Leak source identified: EMP-007"
        │
        ▼
AUDIT LOG: "admin investigated leaked.png, identified EMP-007 at 2026-02-23 14:20:00"
        │
        ▼
Cross-reference with download logs to confirm
```

---

## 5. API Endpoints

### Authentication

All endpoints require `X-API-Key` header.

### Admin Endpoints (Admin API Key Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/admin/upload` | Upload master image |
| GET | `/api/admin/images` | List available images |
| DELETE | `/api/admin/images/{id}` | Delete image |
| GET | `/api/admin/logs` | View download history |
| POST | `/api/investigate` | Extract ID from leaked image |

### Employee Endpoints (Employee API Key Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/images` | List available images |
| GET | `/api/images/{id}/download` | Download with watermark embed |

### Attack Simulation (Admin API Key Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/attack/run` | Run attack simulation |

### Health Check

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

### Async Processing (Performance)

To prevent CPU-intensive DWT operations from blocking the API server, we use asynchronous processing:

```python
from fastapi import BackgroundTasks

@app.post("/api/images/{id}/download")
async def download_image(
    id: str,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Non-blocking download endpoint.
    Returns immediately while watermark processes in background.
    """
    # Create processing job
    job_id = create_job(user_id, image_id)
    
    # Queue background processing
    background_tasks.add_task(process_watermark, job_id, image_id, employee_id)
    
    # Return immediately with job ID
    return {
        "status": "processing",
        "job_id": job_id,
        "message": "Watermark processing started"
    }

@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """Poll for job completion."""
    job = get_job(job_id)
    return {
        "status": job.status,  # "processing", "completed", "failed"
        "download_url": job.result_url if job.status == "completed" else None
    }
```

---

## 7. Security (SSDLC + STRIDE)

### Security Requirements

| ID | Requirement |
|----|-------------|
| REQ-SEC-001 | All API endpoints require authentication via API Key |
| REQ-SEC-002 | Employee IDs must be encrypted using AES-256-GCM |
| REQ-SEC-005 | File uploads must pass Deep MIME Verification (Magic Bytes) |
| REQ-SEC-008 | All uploaded images must be sanitized (EXIF Stripped) |
| REQ-SEC-009 | Code must pass Ruff Security Linting and Bandit SAST |

### Security Tools Pipeline

```yaml
# .github/workflows/security.yml
name: Security Pipeline

on: [push, pull_request]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      # 1. Dependency Vulnerability Scan (SCA)
      - name: Scan dependencies
        run: |
          pip install pip-audit
          pip-audit
      
      # 2. Security Linting (Ruff)
      - name: Run Ruff
        run: |
          pip install ruff
          ruff check .
      
      # 3. Static Application Security Testing (SAST)
      - name: Run Bandit
        run: |
          pip install bandit
          bandit -r app/
      
      # 4. Code Quality & Security (SonarQube)
      - name: SonarCloud Scan
        uses: SonarSource/sonarcloud-github-action@master
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
```

---

## 9. Dependencies

### Production

```txt
fastapi>=0.129.2
uvicorn>=0.41.0
pydantic>=2.12.5
pydantic-settings>=2.13.1
pycryptodome>=3.18.0
invisible-watermark>=0.2.0
python-magic>=0.4.27
Pillow>=12.1.1
python-multipart>=0.0.22
```

### Development

```txt
pytest>=9.0.2
httpx>=0.28.1
bandit>=1.9.3
pip-audit>=2.10.0
ruff>=0.15.4
```

---

## 11. Optional Enhancement: RivaGAN Retraining

> This is an optional enhancement for better geometric attack resilience. Not required for capstone demo.

### Why RivaGAN?

The DWT+DCT algorithm has known limitations:
- ❌ Rotation - may fail
- ❌ Resize - may fail  
- ❌ Crop - may fail

RivaGAN (deep learning) can be trained to survive these attacks.

---

## 12. Summary

| Aspect | Details |
|--------|---------|
| **Main Approach** | Library-based DWT+DCT (no training) |
| **Workflow** | Download-time embedding → Leak investigation |
| **Security** | SSDLC + STRIDE throughout |
| **Backend** | FastAPI with auth, rate limiting, audit logging |
| **Optional** | RivaGAN Retraining for geometric attacks |

---

## 13. Current Status & Implementation Details (March 2026)

### Week 1-2: Foundation & Security Infrastructure
- [x] FastAPI project structure and modular routing
- [x] API Key Authentication (Admin/Employee roles)
- [x] Rate Limiting Middleware (10 req/min with in-memory store)
- [x] Security Headers Middleware (HSTS, CSP, X-Frame-Options, etc.)
- [x] Global Exception Handler (JSON-formatted, no stack traces in responses)

### Week 3-4: Core Endpoints & Logic
- [x] POST `/api/admin/upload` - Master image upload with Deep MIME Verification
- [x] Image Sanitization - Automatic stripping of EXIF/Metadata using Pillow
- [x] GET `/api/images` - Listing images for authorized employees
- [x] GET `/api/images/{id}/download` - Image serving (Watermark ready)
- [x] POST `/api/investigate` - Admin tool for leak attribution

### Week 5-6: Advanced Features & Background Processing
- [x] Async Job Processing - Integration of FastAPI BackgroundTasks for CPU-heavy steganography
- [x] Job Polling System - `/api/jobs/{job_id}` to monitor background tasks
- [x] In-memory job state management (Scalable to Redis)

### Week 7-8: Polish & Production Hardening
- [x] Structured JSON Logging - Custom formatter for ELK/Datadog compatibility
- [x] Pydantic V2 Validation - Detailed schemas with regex (UUID) and constraints
- [x] Enhanced Health Checks - `/health` monitoring storage write access and system time
- [x] SonarQube Integration - `sonar-project.properties` configuration
- [x] Automated Quality Pipeline - Pre-configured Ruff, Bandit, and pip-audit
- [x] Comprehensive Pytest Suite - 100% pass rate on core API flows

---

## 14. Future Enhancements & Post-MVP Roadmap

### 🚀 Immediate Impact
- **Attack Simulation Dashboard**: Implement `POST /api/attack/run` to demonstrate resilience against JPEG compression and Gaussian noise.

### 🛡️ DevSecOps & Deployment
- **Dockerization**: Containerize the application with `Dockerfile` and `docker-compose.yml` for consistent cross-platform deployment.
- **Automated CI Pipeline**: Integrate **GitHub Actions** to automatically trigger security scans (Ruff, Bandit) and unit tests on every push.

### 📊 Observability & Monitoring
- **Admin Dashboard Integration**: Build a real-time monitoring view in the UI to visualize system performance, watermark extraction success rates, and download trends using existing structured logs.
- **Audit Chain Visualization**: Create a visual "Chain of Custody" tool in the UI to track an image from upload through every employee download to final leak investigation.
- **Distributed Tracing**: Implement **X-Request-ID** middleware to track requests across the system for faster debugging and auditability.

---

**Document Version:** Final  
**Last Updated:** March 2026  
**Status:** MVP Implementation Complete
