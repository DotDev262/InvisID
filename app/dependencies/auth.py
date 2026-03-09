import hashlib
import hmac
import time
from typing import Annotated, Optional

from fastapi import Cookie, Depends, Header, HTTPException, Request

from app.config import get_settings

settings = get_settings()

# In-memory rate limit store
rate_limit_store: dict[str, list[float]] = {}


class User:
    def __init__(self, api_key: str, role: str, employee_id: str = None):
        self.api_key = api_key
        self.role = role  # "admin" or "employee"
        self.employee_id = employee_id

async def verify_signature(
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp")
):
    """
    Verify HMAC signature of the request to prevent replay attacks.
    Signature = HMAC-SHA256(key=MASTER_SECRET, msg=timestamp + path)
    """
    if not x_signature or not x_timestamp:
        raise HTTPException(status_code=403, detail="Request signature missing")

    # 1. Check timestamp freshness (5 minute window)
    try:
        ts = float(x_timestamp)
        if abs(time.time() - ts) > 300:
            raise HTTPException(status_code=403, detail="Request expired")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp") from ValueError

    # 2. Verify HMAC
    msg = f"{x_timestamp}{request.url.path}"
    expected = hmac.new(
        settings.MASTER_SECRET.encode(),
        msg.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(x_signature, expected):
        raise HTTPException(status_code=403, detail="Invalid request signature")

async def get_current_user(
    session_token: Optional[str] = Cookie(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    signature: None = Depends(verify_signature)
) -> User:
    """
    Retrieve user from either HttpOnly cookie (preferred) or Header.
    """
    api_key = session_token or x_api_key
    if not api_key:
        raise HTTPException(status_code=401, detail="Authentication required")

    if api_key == settings.ADMIN_API_KEY:
        return User(api_key=api_key, role="admin")
    
    # Map of all authorized employee keys
    employee_map = {
        settings.EMPLOYEE_API_KEY: "EMP-001",
        settings.EMPLOYEE_API_KEY_2: "EMP-002",
        settings.EMPLOYEE_API_KEY_3: "EMP-003",
        settings.EMPLOYEE_API_KEY_4: "CON-004",
        settings.EMPLOYEE_API_KEY_5: "INT-005",
        settings.EMPLOYEE_API_KEY_6: "GST-006",
        settings.EMPLOYEE_API_KEY_7: "EMP-007",
        settings.EMPLOYEE_API_KEY_8: "EMP-008"
    }

    if api_key in employee_map:
        return User(api_key=api_key, role="employee", employee_id=employee_map[api_key])
    
    raise HTTPException(status_code=401, detail="Invalid session or API key")

async def verify_admin_api_key(
    user: User = Depends(get_current_user)
) -> User:
    """Verify admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    await check_rate_limit(user.api_key)
    return user


async def verify_employee_api_key(
    user: User = Depends(get_current_user)
) -> User:
    """Verify employee role."""
    if user.role != "employee":
        raise HTTPException(status_code=403, detail="Employee privileges required")

    await check_rate_limit(user.api_key)
    return user


async def check_rate_limit(api_key: str):
    """Check rate limit for API key."""
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    now = time.time()
    minute_ago = now - 60

    # Clean old entries
    rate_limit_store[key_hash] = [
        t for t in rate_limit_store.get(key_hash, []) if t > minute_ago
    ]

    # Check limit
    if len(rate_limit_store.get(key_hash, [])) >= settings.RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429, detail=f"Rate limit exceeded. Max {settings.RATE_LIMIT_PER_MINUTE} requests/minute."
        )

    # Add current request
    if key_hash not in rate_limit_store:
        rate_limit_store[key_hash] = []
    rate_limit_store[key_hash].append(now)


# Type alias for dependencies
AdminUser = Annotated[User, Depends(verify_admin_api_key)]
EmployeeUser = Annotated[User, Depends(verify_employee_api_key)]
