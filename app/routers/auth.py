from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

class LoginRequest(BaseModel):
    api_key: str

@router.post("/login")
async def login(request: LoginRequest, response: Response):
    """
    Login endpoint that sets a HttpOnly cookie.
    Prevents XSS theft of API keys.
    """
    # Support for multiple employees (Configurable via .env)
    employee_keys = {
        settings.EMPLOYEE_API_KEY: "EMP-001",
        settings.EMPLOYEE_API_KEY_2: "EMP-002",
        settings.EMPLOYEE_API_KEY_3: "EMP-003",
        settings.EMPLOYEE_API_KEY_4: "CON-004",
        settings.EMPLOYEE_API_KEY_5: "INT-005",
        settings.EMPLOYEE_API_KEY_6: "GST-006",
        settings.EMPLOYEE_API_KEY_7: "EMP-007",
        settings.EMPLOYEE_API_KEY_8: "EMP-008"
    }

    role = None
    employee_id = None

    if request.api_key == settings.ADMIN_API_KEY:
        role = "admin"
    elif request.api_key in employee_keys:
        role = "employee"
        employee_id = employee_keys[request.api_key]
    else:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Set HttpOnly cookie
    response.set_cookie(
        key="session_token",
        value=request.api_key,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG  # True in production
    )

    from app.utils.instance import SERVER_INSTANCE_ID

    return {
        "status": "success",
        "role": role,
        "employee_id": employee_id,
        "instance_id": SERVER_INSTANCE_ID,
        "signing_key": settings.MASTER_SECRET # Frontend needs this to sign requests
    }

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session_token")
    return {"status": "success"}
