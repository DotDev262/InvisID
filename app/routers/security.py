from fastapi import APIRouter, Depends, Form
from app.routers.logs import record_log
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/security", tags=["security"])

@router.post("/log-strike")
async def log_security_strike(
    event_type: str = Form(...),
    resource: str = Form(...),
    current_user = Depends(get_current_user)
):
    """
    Records an unauthorized capture attempt (Right-click, Print, Screenshot etc.)
    triggered by the client-side defense wrapper.
    """
    record_log(
        user_id=current_user.id,
        event_type=f"UNAUTHORIZED_{event_type.upper()}",
        resource=resource,
        status="warning",
        details="Client-side defense trigger activated."
    )
    return {"status": "recorded"}
