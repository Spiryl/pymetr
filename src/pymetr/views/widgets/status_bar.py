# views/widgets/status_bar.py
from typing import Optional, Dict
from PySide6.QtWidgets import (
    QStatusBar, QWidget, QHBoxLayout, 
    QLabel, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIcon, QColor

class StatusIndicator(QWidget):
    """Individual status indicator widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._clear_message)
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self.icon_label = QLabel()
        layout.addWidget(self.icon_label)
        
        self.text_label = QLabel()
        self.text_label.setStyleSheet("color: #D4D4D4;")
        layout.addWidget(self.text_label)
        
    def show_message(self, message: str, icon: Optional[QIcon] = None, 
                    color: Optional[str] = None, timeout: int = 0):
        """Show a message with optional icon and timeout."""
        if icon:
            self.icon_label.setPixmap(icon.pixmap(16, 16))
        
        self.text_label.setText(message)
        if color:
            self.text_label.setStyleSheet(f"color: {color};")
            
        if timeout > 0:
            self._timer.start(timeout)
            
    def _clear_message(self):
        """Clear the current message."""
        self.icon_label.clear()
        self.text_label.clear()
        self._timer.stop()

class StatusBar(QStatusBar):
    """Advanced status bar with multiple indicators."""
    
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        # Main status indicator
        self.main_status = StatusIndicator()
        self.addWidget(self.main_status, 1)  # Stretch to take available space
        
        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setMaximumWidth(100)
        self.progress_bar.hide()
        self.addPermanentWidget(self.progress_bar)
        
        # Error/warning indicator
        self.alert_status = StatusIndicator()
        self.addPermanentWidget(self.alert_status)
        
        # Additional indicators can be added as needed
        self.info_status = StatusIndicator()
        self.addPermanentWidget(self.info_status)
        
        # Style the status bar
        self.setStyleSheet("""
            QStatusBar {
                background: #007ACC;
                border-top: 1px solid #1E1E1E;
            }
            QStatusBar::item {
                border: none;
            }
        """)
        
    def _connect_signals(self):
        """Connect to state signals."""
        self.state.status_changed.connect(self._handle_status)
        self.state.status_progress.connect(self._handle_progress)
        self.state.status_error.connect(self._handle_error)
        self.state.status_warning.connect(self._handle_warning)
        self.state.status_info.connect(self._handle_info)
        
    def _handle_status(self, message: str):
        """Handle main status updates."""
        self.main_status.show_message(message)
        
    def _handle_progress(self, percent: float, message: str):
        """Handle progress updates."""
        if percent > 0:
            self.progress_bar.show()
            self.progress_bar.setValue(int(percent))
            if message:
                self.main_status.show_message(message)
        else:
            self.progress_bar.hide()
            
    def _handle_error(self, message: str):
        """Handle error messages."""
        self.alert_status.show_message(
            message,
            # icon=QIcon("path/to/error.png"),
            color="#F14C4C",
            timeout=5000
        )
        
    def _handle_warning(self, message: str):
        """Handle warning messages."""
        self.alert_status.show_message(
            message,
            # icon=QIcon("path/to/warning.png"),
            color="#FFA500",
            timeout=5000
        )
        
    def _handle_info(self, message: str):
        """Handle info messages."""
        self.info_status.show_message(
            message,
            # icon=QIcon("path/to/info.png"),
            color="#4EC9B0",
            timeout=3000
        )