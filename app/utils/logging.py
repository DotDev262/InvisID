import json
import logging
import hmac
from datetime import datetime
from typing import Any, Dict

from app.config import get_settings

settings = get_settings()
HMAC_SECRET = settings.MASTER_SECRET.encode()  # Use MASTER_SECRET for HMAC


class JSONFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format with HMAC integrity."""
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Include extra context if available
        if hasattr(record, "extra_context"):
            log_record["context"] = record.extra_context
            
        # Include exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        # Create HMAC for integrity verification
        log_string = json.dumps(log_record, sort_keys=True)
        log_record["hmac"] = hmac.new(HMAC_SECRET, log_string.encode(), 'sha256').hexdigest()
        
        return json.dumps(log_record)


def create_log_hmac(data: Dict[str, Any]) -> str:
    """Create HMAC for external log verification."""
    return hmac.new(HMAC_SECRET, json.dumps(data, sort_keys=True).encode(), 'sha256').hexdigest()


def verify_log_hmac(data: Dict[str, Any], hmac_signature: str) -> bool:
    """Verify HMAC for incoming log data."""
    expected = create_log_hmac(data)
    return hmac.compare_digest(expected, hmac_signature)


def setup_logging(level: str = "INFO"):
    """Initialize structured JSON logging."""
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    # Add JSON handler
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    # Disable uvicorn's default formatting to use ours
    for name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
        u_logger = logging.getLogger(name)
        u_logger.handlers = []
        u_logger.propagate = True

def get_logger(name: str):
    """Get a named logger."""
    return logging.getLogger(name)
