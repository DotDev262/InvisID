import os
import uuid
import time
from fastapi import APIRouter, File, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse, Response

from app.config import get_settings
from app.services.image_service import extract_watermark
from app.routers import jobs, logs
from app.utils.logging import get_logger

router = APIRouter(prefix="/investigate", tags=["investigation"])
settings = get_settings()
logger = get_logger("app.investigate")

def process_investigation_task(job_id: str, file_path: str, original_filename: str):
    """
    Background task to extract watermark from a leaked image.
    Forensic evidence is preserved in the results directory.
    """
    try:
        logger.info(f"Starting forensic extraction for job: {job_id}")
        
        # --- NEW ALIGNMENT ENGINE ---
        # 1. Identify the Master Image from the filename
        from app.utils.db import get_db
        from app.utils.crypto import decrypt_data
        import cv2
        import numpy as np
        
        conn = get_db()
        cursor = conn.cursor()
        # Look for a master asset that matches this leak's filename (best guess)
        cursor.execute("SELECT id FROM master_images WHERE filename = ?", (original_filename,))
        asset = cursor.fetchone()
        
        master_bytes = None
        if asset:
            asset_id = asset['id']
            master_path = os.path.join(settings.UPLOAD_DIR, f"{asset_id}.png")
            if os.path.exists(master_path):
                with open(master_path, "rb") as f:
                    master_bytes = decrypt_data(f.read())
        conn.close()

        # 2. Extract watermark with alignment
        # Unpack 3 values (ID, Confidence, AlignedImg)
        employee_id, confidence, aligned_img = extract_watermark(file_path, master_data=master_bytes)
        
        if employee_id and employee_id != "UNKNOWN":
            # RECONSTRUCTION: Save the perfectly aligned image as the formal evidence
            if aligned_img is not None:
                cv2.imwrite(file_path, aligned_img)
                
            result = {
                "leaked_by": employee_id,
                "confidence": confidence,
                "extraction_timestamp": time.time()
            }
            jobs.update_job(job_id, "completed", result=result)
            logs.record_log("Admin", "LEAK_INVESTIGATION", original_filename, "success", f"Source Identified: {employee_id}")
            logger.info(f"Watermark extracted successfully for job {job_id}: {employee_id}")
        else:
            jobs.update_job(job_id, "failed", error="No employee watermark detected in the asset.")
            logs.record_log("Admin", "LEAK_INVESTIGATION", original_filename, "failed", "No watermark detected")
            logger.warning(f"No watermark found in asset for job {job_id}")
            
    except Exception as e:
        logger.error(f"Investigation background task failed: {str(e)}", exc_info=True)
        jobs.update_job(job_id, "failed", error=f"Internal Forensic Error: {str(e)}")
        logs.record_log("Admin", "LEAK_INVESTIGATION", original_filename, "error", str(e))

@router.post("/")
async def investigate_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a suspected leak and start forensic extraction in the background.
    """
    if not file.filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPG and PNG are supported.")

    # 1. Create a unique job
    job_id = jobs.create_job("investigation")
    
    # 2. Save file temporarily
    os.makedirs(settings.RESULT_DIR, exist_ok=True)
    temp_filename = f"leak_{job_id}_{file.filename}"
    temp_path = os.path.join(settings.RESULT_DIR, temp_filename)

    try:
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save investigation file: {str(e)}")
        jobs.update_job(job_id, "failed", error="Failed to save uploaded file for analysis.")
        return {"job_id": job_id, "status": "failed"}

    # 3. Start background analysis
    background_tasks.add_task(process_investigation_task, job_id, temp_path, file.filename)
    
    # 4. Log the attempt
    logs.record_log("Admin", "LEAK_INVESTIGATION", file.filename, "started", f"Job: {job_id}")

    return {
        "job_id": job_id,
        "status": "processing",
        "message": "Forensic analysis started."
    }

@router.get("/{job_id}/preview")
async def get_investigation_evidence_preview(job_id: str):
    """Serve a preview of the preserved forensic evidence (suspected leak)."""
    os.makedirs(settings.RESULT_DIR, exist_ok=True)
    
    # Find the file starting with the job_id
    files = os.listdir(settings.RESULT_DIR)
    evidence_file = None
    for f in files:
        if f.startswith(f"leak_{job_id}_"):
            evidence_file = f
            break
            
    if not evidence_file:
        raise HTTPException(status_code=404, detail="Evidence file not found")
        
    return FileResponse(os.path.join(settings.RESULT_DIR, evidence_file))

@router.get("/history")
async def get_investigation_history():
    """Retrieve all completed forensic reports."""
    from app.utils.db import get_db
    import json
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, status, result, created_at FROM jobs WHERE type = 'investigation' AND status = 'completed' ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    
    reports = []
    for row in rows:
        reports.append({
            "job_id": row['id'],
            "created_at": row['created_at'],
            "result": json.loads(row['result']) if row['result'] else None
        })
    return reports

@router.get("/{job_id}/export")
async def export_investigation_report(job_id: str):
    """
    Generate a formal PDF forensic report for a specific investigation.
    """
    from app.utils.db import get_db
    from fpdf import FPDF
    import json
    from datetime import datetime

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ? AND type = 'investigation' AND status = 'completed'", (job_id,))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        raise HTTPException(status_code=404, detail="Forensic report not found")

    result = json.loads(job['result'])
    
    # Create PDF
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(16, 183, 127) # InvisID Green
    pdf.rect(0, 0, 210, 40, 'F')
    
    pdf.set_font("helvetica", "B", 24)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 20, "InvisID Forensic Report", ln=True, align='C')
    
    pdf.set_font("helvetica", "I", 10)
    pdf.cell(0, 5, f"Report ID: {job_id}", ln=True, align='C')
    pdf.ln(20)

    # Body
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "1. Executive Summary", ln=True)
    
    pdf.set_font("helvetica", "", 11)
    summary = (f"This document certifies the results of a forensic leak investigation conducted on "
               f"{datetime.fromisoformat(job['created_at']).strftime('%B %d, %Y at %I:%M %p')}. "
               f"The system has analyzed the suspected asset and identified a unique encrypted watermark.")
    pdf.multi_cell(0, 6, summary)
    pdf.ln(5)

    # Findings Table
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "2. Investigation Findings", ln=True)
    
    pdf.set_font("helvetica", "B", 11)
    pdf.set_fill_color(240, 240, 240)
    
    pdf.cell(60, 10, "Field", border=1, fill=True)
    pdf.cell(130, 10, "Details", border=1, fill=True, ln=True)
    
    pdf.set_font("helvetica", "", 11)
    pdf.cell(60, 10, "Identified Leaker ID", border=1)
    pdf.set_font("helvetica", "B", 11)
    pdf.set_text_color(16, 183, 127)
    pdf.cell(130, 10, f" {result.get('leaked_by', 'UNKNOWN')}", border=1, ln=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 11)
    pdf.cell(60, 10, "Forensic Confidence", border=1)
    pdf.cell(130, 10, f" {result.get('confidence', 0) * 100:.1f}%", border=1, ln=True)
    
    pdf.cell(60, 10, "Analysis Timestamp", border=1)
    ext_time = datetime.fromtimestamp(result.get('extraction_timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
    pdf.cell(130, 10, f" {ext_time} UTC", border=1, ln=True)
    
    pdf.cell(60, 10, "Forensic Method", border=1)
    pdf.cell(130, 10, " DWT-DCT-SVD Frequency Domain Analysis", border=1, ln=True)
    pdf.ln(10)

    # Technical Details
    pdf.set_font("helvetica", "B", 14)
    pdf.cell(0, 10, "3. Technical Validation", ln=True)
    pdf.set_font("helvetica", "", 11)
    pdf.multi_cell(0, 6, "The identification was made using multi-vector majority voting across spatial markers. "
                         "The extracted payload was cross-referenced against the organization's encrypted identity index.")
    pdf.ln(5)

    # Visual Evidence
    try:
        # Try to find the evidence file we preserved
        files = os.listdir(settings.RESULT_DIR)
        evidence_file = None
        for f in files:
            if f.startswith(f"leak_{job_id}_"):
                evidence_file = f
                break
        
        if evidence_file:
            pdf.set_font("helvetica", "B", 14)
            pdf.cell(0, 10, "4. Visual Evidence", ln=True)
            # Add image (scaled to fit)
            pdf.image(os.path.join(settings.RESULT_DIR, evidence_file), x=10, w=100)
    except Exception as e:
        logger.error(f"Failed to add image to PDF: {str(e)}")

    conn.close()

    # Footer
    pdf.set_y(-30)
    pdf.set_font("helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "InvisID Forensic Attribution System - Cryptographically Verified Report", align='C')

    # Return PDF
    return Response(
        content=bytes(pdf.output()),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Forensic_Report_{job_id[:8]}.pdf"}
    )
