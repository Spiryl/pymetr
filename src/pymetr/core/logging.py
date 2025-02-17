# app/logging.py

import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logging(log_to_file: bool = False):
    """Configure application-wide logging with detailed formatting."""
    logger = logging.getLogger('pymetr')
    logger.setLevel(logging.DEBUG)

    # Detailed formatter
    formatter = logging.Formatter(
        '%(levelname)s - %(filename)s:%(lineno)d:%(funcName)s - %(message)s'
    )

    # Console handler
    if not logger.handlers:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        logger.addHandler(console)

        # File handler (optional)
        if log_to_file:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_handler = logging.FileHandler(
                log_dir / f"pymetr_{timestamp}.log",
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    return logger

# Initialize logger
logger = setup_logging()