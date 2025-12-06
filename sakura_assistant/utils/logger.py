import logging
import json
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Config
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "sakura.log"

class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno
        }
        # Add extra fields if available
        if hasattr(record, "props"):
            log_record.update(record.props)
            
        return json.dumps(log_record, ensure_ascii=False)

def setup_logger(name: str = "sakura_assistant"):
    """
    Sets up a structured logger with rotation.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # 1. File Handler (JSON, Rotating)
    # 5 MB max size, keep 3 backups
    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    # 2. Console Handler (Standard Text for Dev)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    return logger

# Global Logger
logger = setup_logger()
