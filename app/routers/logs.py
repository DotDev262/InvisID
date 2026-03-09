import csv
import hashlib
import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.dependencies.auth import AdminUser
from app.models.schemas import AuditLogList
from app.utils.db import get_db

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("/export")
async def export_logs_csv(user: AdminUser):
    """
    Export all audit logs to a CSV file for SIEM integration.
    Includes full cryptographic chain hashes.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, user_id, event_type, resource, status, details, previous_hash, current_hash FROM audit_logs ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Timestamp", "User ID", "Event Type", "Resource", "Status", "Details", "Previous Hash (Link)", "Current Block Hash"])
    
    for row in rows:
        writer.writerow(list(row))
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invisid_audit_logs.csv"}
    )

@router.get("/", response_model=AuditLogList)
async def list_audit_logs(user: AdminUser, event_type: Optional[str] = None):
    """
    List audit logs for the administrator.
    Excludes high-frequency 'started' events to maintain a clean forensic record.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM audit_logs WHERE NOT (event_type = 'LEAK_INVESTIGATION' AND status = 'started')"
    params = []

    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)
    
    query += " ORDER BY timestamp DESC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    logs = [dict(row) for row in rows]
    conn.close()
    return {"logs": logs}

def record_log(user_id: str, event_type: str, resource: str, status: str = "success", details: str = None):
    """Internal helper to record a security event with cryptographic chaining."""
    conn = get_db()
    cursor = conn.cursor()
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # 1. Get the hash of the latest entry
    cursor.execute("SELECT current_hash FROM audit_logs ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    prev_hash = row['current_hash'] if row else "GENESIS_BLOCK"
    
    # 2. Calculate current hash (Chain logic)
    # Hash = SHA256(prev_hash + timestamp + user_id + event_type + status)
    log_content = f"{prev_hash}{timestamp}{user_id}{event_type}{status}{resource}"
    curr_hash = hashlib.sha256(log_content.encode()).hexdigest()
    
    cursor.execute("""
        INSERT INTO audit_logs (timestamp, user_id, event_type, resource, status, details, previous_hash, current_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, user_id, event_type, resource, status, details, prev_hash, curr_hash))
    
    conn.commit()
    conn.close()
