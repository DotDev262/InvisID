from typing import List
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

# Common patterns
UUID_PATTERN = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

class ImageResponse(BaseModel):
    id: str = Field(..., pattern=UUID_PATTERN, description="Unique identifier for the image")
    filename: str = Field(..., max_length=255, description="Name of the image file")
    url: str = Field(..., description="URL to download the watermarked image")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "confidential_plan.jpg",
                "url": "/api/images/550e8400-e29b-41d4-a716-446655440000/download"
            }
        }
    )

class JobResponse(BaseModel):
    id: str = Field(..., pattern=UUID_PATTERN, description="Unique identifier for the background job")
    type: str = Field(..., description="Type of job (e.g., 'investigation', 'watermarking')")
    status: str = Field(..., description="Current status of the job (pending, processing, completed, failed)")
    result: Optional[Any] = Field(None, description="Result of the job if completed")
    error: Optional[str] = Field(None, description="Error message if the job failed")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "type": "investigation",
                "status": "completed",
                "result": {"leaked_by": "EMP-001", "confidence": 0.98}
            }
        }
    )

class UploadResponse(BaseModel):
    id: str = Field(..., pattern=UUID_PATTERN)
    filename: str = Field(..., max_length=255)
    status: str = Field(..., description="Upload status")
    message: str = Field(..., description="User-friendly message")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "original_master.png",
                "status": "uploaded",
                "message": "Master image uploaded successfully"
            }
        }
    )

class InvestigationResponse(BaseModel):
    job_id: str = Field(..., pattern=UUID_PATTERN)
    status: str
    message: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "processing",
                "message": "Investigation started"
            }
        }
    )

class HealthResponse(BaseModel):
    status: str
    storage_ok: bool
    timestamp: datetime

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy",
                "storage_ok": True,
                "timestamp": "2026-03-01T12:00:00Z"
            }
        }
    )

class AuditLogResponse(BaseModel):
    timestamp: datetime
    user_id: str
    event_type: str
    resource: str
    status: str
    details: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2026-03-07T14:30:00Z",
                "user_id": "EMP-001",
                "event_type": "IMAGE_DOWNLOAD",
                "resource": "blueprint_v2.png",
                "status": "success",
                "details": "IP: 192.168.1.5"
            }
        }
    )



class AuditLogList(BaseModel):
    logs: List[AuditLogResponse]
