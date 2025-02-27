# core/logging.py

import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from PySide6.QtCore import QObject, Signal

class CustomFormatter(logging.Formatter):
    def format(self, record):
        # Extract the parent folder name from the full path
        parent_folder = os.path.basename(os.path.dirname(record.pathname))
        # Prepend the parent folder to the filename
        record.filename = f"{parent_folder}/{record.filename}"
        return super().format(record)

class StatusLogHandler(logging.Handler):
    """
    Custom logging handler that emits Qt signals for each log message.
    Used to route log messages to the status bar.
    """
    
    def __init__(self, state):
        """
        Initialize handler with application state.
        
        Args:
            state: ApplicationState instance to emit signals to
        """
        super().__init__()
        self.state = state
        
        # Set custom formatter
        self.setFormatter(logging.Formatter('%(message)s'))
        
        # Set level to INFO by default (don't show DEBUG in status bar)
        self.setLevel(logging.INFO)
        
    def emit(self, record):
        """
        Emit log record as status signal.
        
        Args:
            record: LogRecord instance
        """
        try:
            # Format the message
            msg = self.format(record)
            
            # Route to appropriate status signal based on level
            if record.levelno >= logging.ERROR:
                self.state.status_error.emit(msg)
            elif record.levelno >= logging.WARNING:
                self.state.status_warning.emit(msg)
            elif record.levelno >= logging.INFO:
                self.state.status_info.emit(msg)
                
        except Exception:
            self.handleError(record)

class ConsoleLogHandler(QObject):
    """
    Custom log handler that emits Qt signals for log messages.
    Uses composition instead of multiple inheritance to avoid method conflicts.
    """
    
    log_received = Signal(object)  # Emits the log record
    
    def __init__(self, level=logging.NOTSET):
        super().__init__()
        
        # Create a handler internally
        self._handler = logging.Handler(level)
        self._handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        
        # Add required attributes directly to this object for compatibility
        self.level = level
        self.formatter = self._handler.formatter
        self.filters = self._handler.filters
        
        # Override the emit method of the handler
        self._handler.emit = self._emit_override
    
    def _emit_override(self, record):
        """Internal emit implementation that signals the record."""
        try:
            self.log_received.emit(record)
        except Exception:
            self._handler.handleError(record)
    
    # Public methods that delegate to the internal handler
    def handle(self, record):
        """Handle a log record."""
        if record.levelno >= self.level:
            return self._handler.handle(record)
        return False
    
    def setLevel(self, level):
        """Set the logging level."""
        self.level = level
        return self._handler.setLevel(level)
    
    def setFormatter(self, formatter):
        """Set the formatter."""
        self.formatter = formatter
        return self._handler.setFormatter(formatter)
    
    def format(self, record):
        """Format a log record."""
        return self._handler.format(record)
    
    def close(self):
        """Close the handler."""
        return self._handler.close()
        
    def addFilter(self, filter):
        """Add a filter to the handler."""
        self.filters = self._handler.filters
        return self._handler.addFilter(filter)
        
    def removeFilter(self, filter):
        """Remove a filter from the handler."""
        self.filters = self._handler.filters
        return self._handler.removeFilter(filter)

def setup_logging(log_to_file: bool = False):
    """Configure application-wide logging with detailed formatting."""
    logger = logging.getLogger('pymetr')
    logger.setLevel(logging.DEBUG)

    # Create custom formatter
    formatter = CustomFormatter(
        '%(levelname)-6s:%(lineno)-4d\t%(filename)-36s\t%(funcName)-20s - %(message)s'
    )

    # Console handler
    if not logger.handlers:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        logger.addHandler(console)

        logging.getLogger('pymetr.ui.views').setLevel(logging.CRITICAL)
        logging.getLogger('pymetr.drivers').setLevel(logging.CRITICAL)
        logging.getLogger('pymetr.ui.factories').setLevel(logging.CRITICAL)

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

def setup_status_logging(state, logger_name='pymetr'):
    """
    Set up status bar logging by adding a StatusLogHandler to the logger.
    
    Args:
        state: ApplicationState instance
        logger_name: Name of the logger to attach to
        
    Returns:
        The configured StatusLogHandler instance
    """
    # Get the logger
    logger = logging.getLogger(logger_name)
    
    # Create the handler
    handler = StatusLogHandler(state)
    
    # Add to logger
    logger.addHandler(handler)
    
    return handler

def set_log_level(level, logger_name='pymetr'):
    """
    Set the log level for the specified logger.
    
    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
        logger_name: Name of the logger to modify
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # Also update all handlers
    for handler in logger.handlers:
        if isinstance(handler, (StatusLogHandler, ConsoleLogHandler)):
            # Don't change level for status/console handlers
            # as they may have specific level requirements
            continue
        handler.setLevel(level)

# Initialize logger
logger = setup_logging()