import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Depends

from app.models.schemas import JobResponse
from app.utils.db import get_db
from app.utils.logging import get_logger
from app.dependencies.auth import AdminUser

router = APIRouter(prefix="/jobs", tags=["jobs"])
logger = get_logger("app.jobs")

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str, user: AdminUser):
    """
    Get the status and result of a background job from SQLite.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        logger.warning(f"Job status requested for non-existent ID: {job_id}")
        raise HTTPException(status_code=404, detail="Job not found")
    
    job_dict = dict(row)
    if job_dict["result"]:
        job_dict["result"] = json.loads(job_dict["result"])
    return job_dict

def update_job(job_id: str, status: str, result: Any = None, error: str = None):
    """Internal helper to update job status in SQLite."""
    conn = get_db()
    cursor = conn.cursor()
    
    result_json = json.dumps(result) if result is not None else None
    
    cursor.execute("""
        UPDATE jobs SET status = ?, result = ?, error = ?
        WHERE id = ?
    """, (status, result_json, error, job_id))
    
    if cursor.rowcount == 0:
        logger.error(f"Attempted to update non-existent job: {job_id}")
    else:
        logger.info(f"Job {job_id} updated to {status}")
        
    conn.commit()
    conn.close()

def create_job(job_type: str) -> str:
    """Internal helper to create a new job entry in SQLite."""
    job_id = str(uuid.uuid4())
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO jobs (id, type, status, result, error)
        VALUES (?, ?, ?, ?, ?)
    """, (job_id, job_type, "pending", None, None))
    
    conn.commit()
    conn.close()
    logger.info(f"Job {job_id} created (type: {job_type})")
    return job_id
