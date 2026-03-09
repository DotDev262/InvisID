import pytest
from unittest.mock import patch, MagicMock
from app.main import app
from app.config import get_settings
from app.middleware.rate_limit import clear_rate_limits

settings = get_settings()

def test_rate_limiting(client):
    """
    Simulate a rapid burst of requests to trigger the 429 Rate Limit.
    """
    clear_rate_limits()
    # The limit is set to 60 per minute in our current config
    # We will make 61 requests quickly.
    
    responses = []
    for _ in range(settings.RATE_LIMIT_PER_MINUTE + 1):
        # Using a route that is NOT excluded from rate limiting
        responses.append(client.get("/api/images/"))
    
    # Check that at least the last request was rate limited
    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes
    
    # Verify the error message
    limit_error = next(r for r in responses if r.status_code == 429)
    assert "Rate limit exceeded" in limit_error.json()["detail"]

def test_sql_injection_protection(client):
    """
    Attempt a SQL injection payload on an ID parameter.
    We expect a 404 Not Found (safe) instead of a database crash or leaked data.
    """
    clear_rate_limits()
    # Payload designed to always return true if executed as raw SQL
    sqli_payload = "any_id' OR '1'='1"
    
    # Attempt to use this payload in an authenticated route (mocking auth)
    from app.dependencies.auth import get_current_user, User
    app.dependency_overrides[get_current_user] = lambda: User(api_key="mock", role="admin")
    
    # If the SQLi worked, it might return a list of images it shouldn't
    # If it's safe (parameterized), it will just look for an image named "any_id' OR '1'='1" and fail.
    response = client.get(f"/api/images/{sqli_payload}/preview")
    
    # 404 is the correct behavior for a non-existent asset ID
    assert response.status_code == 404
    
    # Cleanup overrides
    app.dependency_overrides = {}

def test_path_traversal_protection(client):
    """
    Attempt to access files outside the storage directory.
    """
    clear_rate_limits()
    traversal_payload = "../../../../../etc/passwd"
    
    from app.dependencies.auth import get_current_user, User
    app.dependency_overrides[get_current_user] = lambda: User(api_key="mock", role="admin")
    
    response = client.get(f"/api/images/{traversal_payload}/download")
    
    # Should not succeed. 404 is expected because the ID doesn't exist.
    assert response.status_code == 404
    
    app.dependency_overrides = {}

def test_hmac_signature_bypass_protection(client):
    """
    Attempt to access an admin route without a valid HMAC signature.
    """
    clear_rate_limits()
    import time
    fresh_timestamp = str(int(time.time()))
    # We don't override current_user here, so it uses real middleware
    response = client.get("/api/admin/metrics", headers={
        "X-Timestamp": fresh_timestamp,
        "X-Signature": "invalid_signature_here"
    })
    
    # 403 Forbidden is expected for invalid signatures
    assert response.status_code == 403
    assert "Invalid request signature" in response.json()["detail"]

def test_expired_request_protection(client):
    """
    Attempt to use a valid-looking signature but with an expired timestamp.
    """
    clear_rate_limits()
    old_timestamp = str(int(1000000)) # Way in the past
    response = client.get("/api/admin/metrics", headers={
        "X-Timestamp": old_timestamp,
        "X-Signature": "some_signature"
    })
    
    # 403 Forbidden is expected for expired requests
    assert response.status_code == 403
    assert "Request expired" in response.json()["detail"]

@patch("app.routers.admin.get_db")
def test_forensic_integrity_violation_detection(mock_db, client):
    """
    Test that the Security Diagnostic can detect a tampered log chain.
    """
    # Create a mock DB response with a broken hash chain
    mock_cursor = MagicMock()
    mock_db.return_value.cursor.return_value = mock_cursor
    
    # Simulate a log where the previous_hash doesn't link to anything
    mock_cursor.fetchall.side_effect = [
        [{"previous_hash": "WRONG_HASH", "current_hash": "abc", "timestamp": "...", "user_id": "...", "event_type": "...", "status": "...", "resource": "..."}],
        [] # For the asset integrity check
    ]
    
    from app.dependencies.auth import get_current_user, User
    app.dependency_overrides[get_current_user] = lambda: User(api_key="mock", role="admin")
    
    response = client.get("/api/admin/diagnostic")
    
    assert response.status_code == 200
    assert response.json()["status"] == "fail"
    assert "Chain broken" in response.json()["checks"]["log_chain"]["issues"][0]
    
    app.dependency_overrides = {}
