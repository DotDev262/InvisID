import hashlib
import time
from typing import Annotated

from fastapi import Depends, Header, HTTPException

from app.config import get_settings

settings = get_settings()

# In-memory rate limit store
rate_limit_store: dict[str, list[float]] = {}


class User:
    def __init__(self, api_key: str, role: str, employee_id: str = None):
        self.api_key = api_key
        self.role = role  # "admin" or "employee"
        self.employee_id = employee_id


async def verify_admin_api_key(
    x_api_key: Annotated[str, Header(alias="X-API-Key")],
) -> User:
    """Verify admin API key."""
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check rate limit
    await check_rate_limit(x_api_key)

    return User(api_key=x_api_key, role="admin")


async def verify_employee_api_key(
    x_api_key: Annotated[str, Header(alias="X-API-Key")],
) -> User:
    """Verify employee API key."""
    if x_api_key != settings.EMPLOYEE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check rate limit
    await check_rate_limit(x_api_key)

    # For employees, we could look up their ID from the key
    return User(api_key=x_api_key, role="employee", employee_id="EMP-001")


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
            status_code=429, detail="Rate limit exceeded. Max 10 requests/minute."
        )

    # Add current request
    if key_hash not in rate_limit_store:
        rate_limit_store[key_hash] = []
    rate_limit_store[key_hash].append(now)


# Type alias for dependencies
AdminUser = Annotated[User, Depends(verify_admin_api_key)]
EmployeeUser = Annotated[User, Depends(verify_employee_api_key)]
