# pymetr/ui/views/scpi_console.py
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QLabel, QSplitter
)
from PySide6.QtGui import QColor, QTextCursor, QFont

from pymetr.models.device import Device
from pymetr.core.logging import logger

class SCPIConsole(QWidget):
    """
    Interactive console for SCPI command control of an instrument.
    Provides command entry, read/write/query operations, and command history.
    """
    
    def __init__(self, state, model_id, parent=None):
        super().__init__(parent)
        self.state = state
        self.model_id = model_id
        self.device = self.state.get_model(model_id) if model_id else None
        
        # Setup UI
        self._setup_ui()
        
        # Initialize with current state
        self._update_connection_state()
        
        # Connect to device connection change signal
        if self.device:
            self.device.connection_changed.connect(self._update_connection_state)
            
            # Set window title based on device
            name = self.device.get_property('name', 'Instrument')
            self.setWindowTitle(f"SCPI: {name}")
        
    def _setup_ui(self):
        """Set up the console UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        
        # Output display
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QTextEdit.WidgetWidth)
        
        # Set fixed-width font for better command display
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.output.setFont(font)
        
        # Add to layout
        layout.addWidget(self.output)
        
        # Command entry area
        cmd_layout = QHBoxLayout()
        cmd_layout.setSpacing(2)
        
        # Command label
        cmd_label = QLabel("Command:")
        cmd_layout.addWidget(cmd_label)
        
        # Command entry
        self.cmd_entry = QLineEdit()
        self.cmd_entry.setPlaceholderText("Enter SCPI command...")
        self.cmd_entry.returnPressed.connect(self._on_query)
        cmd_layout.addWidget(self.cmd_entry, 1)  # Stretch
        
        # Action buttons
        self.write_btn = QPushButton("Write")
        self.write_btn.clicked.connect(self._on_write)
        cmd_layout.addWidget(self.write_btn)
        
        self.read_btn = QPushButton("Read")
        self.read_btn.clicked.connect(self._on_read)
        cmd_layout.addWidget(self.read_btn)
        
        self.query_btn = QPushButton("Query")
        self.query_btn.clicked.connect(self._on_query)
        cmd_layout.addWidget(self.query_btn)
        
        # Add to main layout
        layout.addLayout(cmd_layout)
        
        # Install event filter for keyboard shortcuts
        self.cmd_entry.installEventFilter(self)

    def _update_connection_state(self, connected=None):
        """Update UI based on connection state."""
        if connected is None and self.device:
            connected = self.device.get_property('is_connected', False)
        
        # Enable/disable controls based on connection state
        self.cmd_entry.setEnabled(connected)
        self.write_btn.setEnabled(connected)
        self.read_btn.setEnabled(connected)
        self.query_btn.setEnabled(connected)
        
        # Connect to instrument signals if connected
        if connected and self.device and hasattr(self.device, 'instrument') and self.device.instrument:
            self._connect_signals()
            self._append_text(f"Connected to {self.device.get_property('name', 'Instrument')}", "normal")
        else:
            self._append_text("No instrument connected", "error")

    def _connect_signals(self):
        """Connect to device instrument signals."""
        if (self.device and hasattr(self.device, 'instrument') and 
            self.device.instrument is not None):
            # Disconnect any existing connections first
            try:
                self.device.instrument.commandSent.disconnect(self._on_command_sent)
                self.device.instrument.responseReceived.disconnect(self._on_response_received)
                self.device.instrument.exceptionOccured.disconnect(self._on_exception)
            except (TypeError, RuntimeError):
                # Signal was not connected
                pass
                
            # Connect signals
            self.device.instrument.commandSent.connect(self._on_command_sent)
            self.device.instrument.responseReceived.connect(self._on_response_received)
            self.device.instrument.exceptionOccured.connect(self._on_exception)
            
            logger.debug(f"SCPI Console connected to instrument signals for {self.device.get_property('name')}")
            
    def _append_text(self, text, style="normal"):
        """
        Add text to the console output with appropriate styling.
        
        Args:
            text: Text to append
            style: Style name (normal, command, response, error)
        """
        # Create color based on style
        color = QColor()
        if style == "command":
            color = QColor("#4CAF50")  # Green
        elif style == "response":
            color = QColor("#2196F3")  # Blue
        elif style == "error":
            color = QColor("#F44336")  # Red
        else:
            color = QColor("#CCCCCC")  # Gray
            
        # Set text color
        self.output.setTextColor(color)
        
        # Add text
        self.output.append(text)
        
        # Scroll to bottom
        self.output.moveCursor(QTextCursor.End)
        
    def _on_write(self):
        """Handle Write button click."""
        command = self.cmd_entry.text().strip()
        if not command:
            return
            
        # Get current instrument instance (may have changed since initialization)
        instrument = None
        if self.device and hasattr(self.device, 'instrument'):
            instrument = self.device.instrument
            
        # Send the command
        if instrument:
            try:
                instrument.write(command)
                # Command will be displayed through signal handler
            except Exception as e:
                self._append_text(f"Error: {str(e)}", "error")
        else:
            self._append_text("No instrument connected", "error")
            
        # Clear entry
        self.cmd_entry.clear()
        
    def _on_read(self):
        """Handle Read button click."""
        if self.device and self.device.instrument:
            try:
                self.device.instrument.read()
                # Display will happen through signal handler
            except Exception as e:
                self._append_text(f"Error: {str(e)}", "error")
        else:
            self._append_text("No instrument connected", "error")
            
    def _on_query(self):
        """Handle Query button click."""
        command = self.cmd_entry.text().strip()
        if not command:
            return
            
        # Send the command
        if self.device and self.device.instrument:
            try:
                self.device.instrument.query(command)
                # Display will happen through signal handler
            except Exception as e:
                self._append_text(f"Error: {str(e)}", "error")
        else:
            self._append_text("No instrument connected", "error")
            
        # Clear entry
        self.cmd_entry.clear()
        
    def _on_command_sent(self, command):
        """Handle command sent signal."""
        self._append_text(f">> {command}", "command")
        
    def _on_response_received(self, command, response):
        """Handle response received signal."""
        self._append_text(f"<< {response}", "response")
        
    def _on_exception(self, error):
        """Handle exception signal."""
        self._append_text(f"ERROR: {error}", "error")
        
    def eventFilter(self, obj, event):
        """Filter events for custom behavior."""
        # This allows keyboard shortcuts like Ctrl+W, etc.
        return super().eventFilter(obj, event)