from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class ImageResponse(BaseModel):
    id: str
    filename: str
    url: str

class JobResponse(BaseModel):
    id: str
    type: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None

class UploadResponse(BaseModel):
    id: str
    filename: str
    status: str
    message: str

class InvestigationResponse(BaseModel):
    job_id: str
    status: str
    message: str

class HealthResponse(BaseModel):
    status: str
