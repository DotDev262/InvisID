import os
import sqlite3

from app.config import get_settings

settings = get_settings()
DB_PATH = os.path.join(os.path.dirname(settings.UPLOAD_DIR), "invisid.db")

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Audit Logs Table (Cryptographically Chained)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_id TEXT,
            event_type TEXT,
            resource TEXT,
            status TEXT,
            details TEXT,
            previous_hash TEXT,
            current_hash TEXT
        )
    """)
    
    # Jobs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            type TEXT,
            status TEXT,
            result TEXT,
            error TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Master Images Table (Integrity Tracking)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS master_images (
            id TEXT PRIMARY KEY,
            filename TEXT,
            sha256 TEXT,
            uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            deleted_at DATETIME DEFAULT NULL
        )
    """)
    
    # Check if deleted_at exists, if not add it (for migration)
    try:
        cursor.execute("ALTER TABLE master_images ADD COLUMN deleted_at DATETIME DEFAULT NULL")
    except sqlite3.OperationalError:
        pass # Column already exists
    
    conn.commit()
    conn.close()

# Initialize on import
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
init_db()
