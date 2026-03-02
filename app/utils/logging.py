import json
import logging
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom formatter to output logs in JSON format."""
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
            
        # Include exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

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
