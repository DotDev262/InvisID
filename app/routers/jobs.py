import uuid
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.models.schemas import JobResponse
from app.utils.logging import get_logger

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = get_logger("app.jobs")

# In-memory job store
jobs: Dict[str, Dict[str, Any]] = {}

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """
    Get the status and result of a background job.
    
    Background jobs include watermark extraction for investigation. 
    Poll this endpoint using the `job_id` returned when starting the task.
    """
    if job_id not in jobs:
        logger.warning(f"Job status requested for non-existent ID: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

def update_job(job_id: str, status: str, result: Any = None, error: str = None):
    """Internal helper to update job status and logs changes."""
    if job_id in jobs:
        jobs[job_id]["status"] = status
        if result is not None:
            jobs[job_id]["result"] = result
        if error is not None:
            jobs[job_id]["error"] = error
        
        logger.info(f"Job {job_id} updated to {status}")
    else:
        logger.error(f"Attempted to update non-existent job: {job_id}")

def create_job(job_type: str) -> str:
    """Internal helper to create a new job entry."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "type": job_type,
        "status": "pending",
        "result": None,
        "error": None
    }
    logger.info(f"Job {job_id} created (type: {job_type})")
    return job_id
