import logging
from datetime import datetime
from PySide6.QtCore import Qt, Signal, QObject, QSize
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                               QPushButton, QDockWidget, QComboBox, QLabel)
from PySide6.QtGui import QTextCursor, QColor, QFont, QTextCharFormat, QTextBlockFormat

from pymetr.core.logging import logger, ConsoleLogHandler

class ConsoleDock(QDockWidget):
    """
    Dock widget that displays console/log output.
    """
    
    def __init__(self, parent=None):
        super().__init__("Console", parent)
        self.setObjectName("ConsoleDock")
        self.setAllowedAreas(Qt.BottomDockWidgetArea)
        
        # Create main widget
        self.console_widget = QWidget()
        self.setWidget(self.console_widget)
        
        # Create layout
        layout = QVBoxLayout(self.console_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Create toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)
        
        # Add buttons
        self.clear_button = QPushButton("Clear")
        self.clear_button.setMaximumWidth(60)
        self.clear_button.clicked.connect(self._clear_console)
        toolbar_layout.addWidget(self.clear_button)
        
        # Add spacer
        toolbar_layout.addStretch(1)
        
        # Add to main layout
        layout.addLayout(toolbar_layout)
        
        # Create console output text edit
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setLineWrapMode(QTextEdit.NoWrap)
        
        # Set font
        font = QFont("Consolas, Courier New, monospace")
        font.setPointSize(9)
        self.console_output.setFont(font)
        
        layout.addWidget(self.console_output, 1)  # 1 = stretch factor
        
        # Set up log handler
        self.log_handler = ConsoleLogHandler()
        self.log_handler.log_received.connect(self._on_log_message)
        
        # Set minimum size
        self.setMinimumHeight(150)
        
        # Connect to logger
        root_logger = logging.getLogger('pymetr')
        root_logger.addHandler(self.log_handler)
        
        # Format for different log levels
        self.level_formats = {
            logging.DEBUG: self._create_format(QColor("#6C757D")),  # Gray
            logging.INFO: self._create_format(QColor("#FFFFFF")),   # White
            logging.WARNING: self._create_format(QColor("#FFC107")), # Yellow
            logging.ERROR: self._create_format(QColor("#F44336")),  # Red
            logging.CRITICAL: self._create_format(QColor("#E91E63")) # Pink
        }
    
    def _create_format(self, color):
        """Create text format for a log level."""
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        return fmt
    
    def _on_log_message(self, record):
        """Handle log message."""
        # Get format for this level
        fmt = self.level_formats.get(record.levelno, self.level_formats[logging.INFO])
        
        # Format timestamp
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        
        # Format message
        message = f"[{time_str}] {self.log_handler.format(record)}"
        
        # Append to console with formatting
        cursor = self.console_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(message + "\n", fmt)
        
        # Auto-scroll
        self.console_output.setTextCursor(cursor)
        self.console_output.ensureCursorVisible()
    
    def _clear_console(self):
        """Clear console output."""
        self.console_output.clear()
        
    def set_log_level(self, level):
        """Set the logging level for this handler."""
        self.log_handler.setLevel(level)
        
    def closeEvent(self, event):
        """Handle dock close event."""
        # Remove handler when dock is closed
        root_logger = logging.getLogger('pymetr')
        root_logger.removeHandler(self.log_handler)
        super().closeEvent(event)