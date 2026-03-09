import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.config import get_settings

settings = get_settings()

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def admin_auth_headers():
    return {"Authorization": f"Bearer {settings.ADMIN_API_KEY}"}

@pytest.fixture
def employee_auth_headers():
    return {"Authorization": f"Bearer {settings.EMPLOYEE_API_KEY}"}
