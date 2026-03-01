from fastapi.testclient import TestClient
import pytest
import os
import shutil

from app.main import app
from app.config import get_settings

client = TestClient(app)
settings = get_settings()

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "InvisID API", "status": "running"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

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
    # Create dummy image
    image_path = "test_image.jpg"
    with open(image_path, "wb") as f:
        f.write(b"dummy image content")
    
    with open(image_path, "rb") as f:
        response = client.post(
            "/api/admin/upload",
            headers={"X-API-Key": settings.ADMIN_API_KEY},
            files={"file": ("test_image.jpg", f, "image/jpeg")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["status"] == "uploaded"
    
    os.remove(image_path)
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
    # Create dummy image
    image_path = "leaked_image.jpg"
    with open(image_path, "wb") as f:
        f.write(b"leaked image content")
        
    with open(image_path, "rb") as f:
        response = client.post(
            "/api/investigate",
            headers={"X-API-Key": settings.ADMIN_API_KEY},
            files={"file": ("leaked_image.jpg", f, "image/jpeg")}
        )
    
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "processing"
    
    os.remove(image_path)
    
    # Check job status
    job_id = data["job_id"]
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    assert response.json()["id"] == job_id
