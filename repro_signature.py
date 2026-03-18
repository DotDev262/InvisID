import hmac
import hashlib
import time
from fastapi.testclient import TestClient
from app.main import app
from app.config import get_settings
from app.utils.crypto import derive_signing_key

settings = get_settings()
client = TestClient(app)

def test_valid_signature():
    path = "/api/admin/metrics"
    timestamp = str(int(time.time()))
    api_key = settings.ADMIN_API_KEY
    
    # 1. Derive the same key the frontend and backend should now use
    signing_key = derive_signing_key(api_key)
    
    # 2. Generate signature
    msg = f"{timestamp}{path}"
    signature = hmac.new(
        signing_key.encode(),
        msg.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # 3. Send request
    headers = {
        "X-Timestamp": timestamp,
        "X-Signature": signature,
        "X-API-Key": api_key
    }
    
    response = client.get(path, headers=headers)
    
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200
    assert "total_assets" in response.json()

if __name__ == "__main__":
    try:
        test_valid_signature()
        print("\nSUCCESS: Signature verification passed with derived key!")
    except Exception as e:
        print(f"\nFAILURE: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
