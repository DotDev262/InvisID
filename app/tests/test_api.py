from fastapi.testclient import TestClient
import pytest
import os
import shutil
import re
from PIL import Image
from io import BytesIO

from app.main import app
from app.config import get_settings

client = TestClient(app)
settings = get_settings()

def create_test_image():
    """Create a valid small JPEG image in memory."""
    file = BytesIO()
    image = Image.new('RGB', (100, 100), color='red')
    image.save(file, 'jpeg')
    file.seek(0)
    return file

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "InvisID API", "status": "running"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "storage_ok" in data
    assert "timestamp" in data
    assert data["storage_ok"] is True

def test_unauthorized_upload():
    response = client.post("/api/admin/upload")
    assert response.status_code == 422 # Missing headers

def test_admin_upload_invalid_key():
    response = client.post(
        "/api/admin/upload",
        headers={"X-API-Key": "wrong-key"}
    )
    assert response.status_code == 401

def test_admin_upload_valid():
    # Create valid dummy image
    img_data = create_test_image()
    
    response = client.post(
        "/api/admin/upload",
        headers={"X-API-Key": settings.ADMIN_API_KEY},
        files={"file": ("test_image.jpg", img_data, "image/jpeg")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", data["id"])
    assert data["status"] == "uploaded"
    
    # Clean up uploaded file
    uploaded_path = os.path.join(settings.UPLOAD_DIR, data["filename"])
    if os.path.exists(uploaded_path):
        os.remove(uploaded_path)

def test_list_images():
    response = client.get(
        "/api/images/",
        headers={"X-API-Key": settings.EMPLOYEE_API_KEY}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_investigate_start():
    # Create valid dummy image
    img_data = create_test_image()
        
    response = client.post(
        "/api/investigate",
        headers={"X-API-Key": settings.ADMIN_API_KEY},
        files={"file": ("leaked_image.jpg", img_data, "image/jpeg")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", data["job_id"])
    assert data["status"] == "processing"
    
    # Check job status
    job_id = data["job_id"]
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["id"] == job_id
