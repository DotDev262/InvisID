from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
import uuid

from app.dependencies.auth import AdminUser, EmployeeUser
from app.models.schemas import JobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

# In-memory job store
jobs: Dict[str, Dict[str, Any]] = {}

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get the status of a background job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

def update_job(job_id: str, status: str, result: Any = None, error: str = None):
    """Helper to update job status."""
    if job_id in jobs:
        jobs[job_id]["status"] = status
        if result is not None:
            jobs[job_id]["result"] = result
        if error is not None:
            jobs[job_id]["error"] = error

def create_job(job_type: str) -> str:
    """Helper to create a new job."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "type": job_type,
        "status": "pending",
        "result": None,
        "error": None
    }
    return job_id
