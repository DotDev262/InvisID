# InvisID - Leak Attribution System for Sensitive Images
## Trace Leaked Product Designs Back to the Source Employee

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-1.0.0-00a393.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

InvisID is a **leak attribution system** that traces leaked sensitive images back to the source employee using invisible watermarking.

---

## Key Features

🔐 **Hardened Security**
- **Deep MIME Verification**: Using `python-magic` to prevent extension-spoofing attacks by inspecting magic bytes.
- **Image Sanitization**: Automatic stripping of EXIF metadata (GPS, device info) using `Pillow` to prevent information leakage.
- **API Key Authentication**: Role-based access control for Admins and Employees.
- **Rate Limiting**: Integrated protection against brute-force and DoS (10 req/min).
- **Security Headers**: Production-ready middleware for HSTS, CSP, X-Frame-Options, and more.

📊 **Enterprise Observability**
- **Structured JSON Logging**: Machine-readable logs formatted for ELK, Datadog, or CloudWatch.
- **Comprehensive Health Checks**: Real-time monitoring of storage write-access and system integrity.
- **OpenAPI Documentation**: Interactive documentation at `/api/docs` with detailed models and examples.

🛠️ **Security Pipeline & Code Quality**
- **Ruff**: High-performance linter enforcing security (`S`), bugbear (`B`), and complexity (`C90`) rules.
- **Bandit**: Static Application Security Testing (SAST) to find common security issues.
- **pip-audit**: Software Composition Analysis (SCA) to detect vulnerable dependencies.
- **SonarQube Ready**: Pre-configured for deep code quality analysis and security hotspots.

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| **FastAPI** | Modern web framework with auto-generated OpenAPI docs |
| **Pillow** | Image processing, metadata stripping, and sanitization |
| **python-magic** | Deep file type inspection via magic bytes |
| **Pydantic V2** | Type-safe data validation and environment settings |
| **UV** | High-performance Python package and project management |
| **Ruff** | Security-focused linting and code formatting |
| **Bandit / pip-audit** | Automated security scanning for code and dependencies |
| **SonarQube** | Centralized quality gate and security dashboard |

---

## Installation

### Prerequisites
- Python 3.12+
- [UV package manager](https://github.com/astral-sh/uv)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/DotDev262/InvisID.git
cd InvisID

# 2. Install dependencies
uv sync

# 3. Set up environment variables
# Ensure app/.env exists with required secrets
echo "MASTER_SECRET=your-32-character-secret-here" > app/.env

# 4. Run the application
cd app
uv run uvicorn main:app --reload
```

The application will be available at `http://localhost:8000`
Interactive API Docs: `http://localhost:8000/api/docs`

---

## Usage

### Admin Workflow (Security Team)
1. **Upload Master Images**: `POST /api/admin/upload` (Automatically sanitizes and strips metadata).
2. **Investigate a Leak**: `POST /api/investigate` (Starts background job to extract encrypted watermark).
3. **Poll Results**: `GET /api/jobs/{job_id}` (Check status of extraction).

### Employee Workflow
1. **List Images**: `GET /api/images` (See available designs).
2. **Download**: `GET /api/images/{id}/download` (Get unique watermarked copy tied to your ID).

---

## Security Analysis

Run the built-in security suite to verify system integrity:

```bash
cd app
# 1. Linting & Security check (Ruff)
uv run ruff check .

# 2. SAST Scanning (Bandit)
uv run bandit -r . -x ./tests

# 3. Dependency Audit (pip-audit)
uv run pip-audit
```

---

## License
MIT License - See [LICENSE](LICENSE) for details
