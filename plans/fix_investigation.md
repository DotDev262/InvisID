# Plan: Fix Investigation UI and Secure Endpoints

The investigation feature is currently failing due to a mix of missing trailing slashes in frontend API calls (causing 307 redirects) and missing authentication/signature verification in several backend routers.

## Objective
- Fix the Investigation Lab UI to correctly call the backend.
- Secure `app/routers/investigate.py` and `app/routers/jobs.py` endpoints.
- Ensure the forensic report export works correctly with `fpdf2`.

## Proposed Changes

### 1. Backend: Secure `app/routers/investigate.py`
- Import `AdminUser` and `Depends`.
- Add `user: AdminUser` dependency to all endpoints:
    - `POST /api/investigate/`
    - `GET /api/investigate/{job_id}/preview`
    - `GET /api/investigate/history`
    - `GET /api/investigate/{job_id}/export`

### 2. Backend: Secure `app/routers/jobs.py`
- Import `User` and `get_current_user` (or `AdminUser` if we want to restrict it further). 
- Since both admins and employees might need to check job status (though currently only used by admins for investigation), we'll use `AdminUser` to be safe for now, as jobs currently only store sensitive investigation results.
- Add `user: AdminUser` to `get_job_status`.

### 3. Frontend: Fix `app/static/admin/investigation.html`
- Update `startInvestigation` to use `/api/investigate/` (with trailing slash).
- Update `pollJob` to use `/api/jobs/${jobId}` (FastAPI might still redirect this, better use `/api/jobs/${jobId}/` if the router defines it with a slash, but `jobs.py` defines it as `/{job_id}`).
- Wait, `jobs.py` has `@router.get("/{job_id}")`. No trailing slash in definition.
- `investigate.py` has `@router.post("/")` with prefix `/investigate`, so it's `/api/investigate/`.
- `investigate.py` has `@router.get("/history")` -> `/api/investigate/history`.
- `investigate.py` has `@router.get("/{job_id}/preview")` -> `/api/investigate/{job_id}/preview`.
- `investigate.py` has `@router.get("/{job_id}/export")` -> `/api/investigate/{job_id}/export`.

### 4. Backend: Fix `fpdf2` output in `app/routers/investigate.py`
- Ensure `pdf.output()` is correctly handled (it returns `bytearray` or `bytes` depending on version/arguments, `bytes(pdf.output())` is generally safe).

## Implementation Steps

1. **Modify `app/routers/investigate.py`**:
    - Add imports: `from fastapi import ..., Depends` and `from app.dependencies.auth import AdminUser`.
    - Update all route functions to include `user: AdminUser`.

2. **Modify `app/routers/jobs.py`**:
    - Add imports: `from fastapi import ..., Depends` and `from app.dependencies.auth import AdminUser`.
    - Update `get_job_status` to include `user: AdminUser`.

3. **Modify `app/static/admin/investigation.html`**:
    - Change `fetch('/api/investigate'` to `fetch('/api/investigate/'` in `startInvestigation`.

4. **Verification**:
    - Run the reproduction script `scripts/repro_investigate.py` (updated if needed) to confirm 200 OK and successful job creation.
    - Manually verify the UI if possible (simulated via `curl` or reproduction script).

## Verification Plan

- **Automated Test**: Run `scripts/repro_investigate.py` using `devenv shell -- uv run python ...`.
- **Manual Check**: Verify that `GET /api/investigate/history` now returns 403 without a signature/API key.
- **Manual Check**: Verify that `POST /api/investigate/` works with a signature and trailing slash.
