from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFormLayout, QGroupBox
)
from PySide6.QtCore import Qt, Slot

from pymetr.core.logging import logger

class ConnectionDialog(QDialog):
    """Dialog for manual instrument connection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result_info = {}
        self._setup_ui()
        
    def _setup_ui(self):
        """Initialize dialog UI."""
        self.setWindowTitle("Connect to Instrument")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Connection type selection
        connection_group = QGroupBox("Connection Type")
        connection_layout = QVBoxLayout(connection_group)
        
        self.conn_type = QComboBox()
        self.conn_type.addItems(["VISA", "TCP/IP", "Serial"])
        self.conn_type.currentTextChanged.connect(self._connection_type_changed)
        connection_layout.addWidget(self.conn_type)
        
        layout.addWidget(connection_group)
        
        # Connection parameters
        self.params_group = QGroupBox("Connection Parameters")
        self.params_layout = QFormLayout(self.params_group)
        
        # VISA parameters (default)
        self.visa_resource = QLineEdit()
        self.visa_resource.setPlaceholderText("e.g., TCPIP0::192.168.1.10::5025::SOCKET")
        self.params_layout.addRow("Resource String:", self.visa_resource)
        
        # TCP/IP parameters (initially hidden)
        self.ip_address = QLineEdit()
        self.ip_address.setPlaceholderText("e.g., 192.168.1.10")
        self.params_layout.addRow("IP Address:", self.ip_address)
        
        self.ip_port = QLineEdit("5025")  # Default SCPI port
        self.params_layout.addRow("Port:", self.ip_port)
        
        # Serial parameters (initially hidden)
        self.serial_port = QLineEdit()
        self.serial_port.setPlaceholderText("e.g., COM1 or /dev/ttyUSB0")
        self.params_layout.addRow("Port:", self.serial_port)
        
        self.baud_rate = QComboBox()
        self.baud_rate.addItems(["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
        self.baud_rate.setCurrentText("9600")
        self.params_layout.addRow("Baud Rate:", self.baud_rate)
        
        # Common parameters
        self.timeout = QLineEdit("5")
        self.params_layout.addRow("Timeout (s):", self.timeout)
        
        layout.addWidget(self.params_group)
        
        # Initial state
        self._connection_type_changed(self.conn_type.currentText())
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._handle_connect)
        button_layout.addWidget(self.connect_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def _connection_type_changed(self, connection_type):
        """Handle connection type change."""
        # Hide all params first
        for row in range(self.params_layout.rowCount()):
            label_item = self.params_layout.itemAt(row, QFormLayout.LabelRole)
            if label_item:
                label_widget = label_item.widget()
                if label_widget:
                    label_widget.setVisible(False)
            
            field_item = self.params_layout.itemAt(row, QFormLayout.FieldRole)
            if field_item:
                field_widget = field_item.widget()
                if field_widget:
                    field_widget.setVisible(False)
        
        # Show only relevant params
        if connection_type == "VISA":
            # Show VISA and common params
            for row in range(2):  # Resource string + timeout
                self._set_row_visible(row, True)
            
        elif connection_type == "TCP/IP":
            # Show IP, port and common params
            for row in range(2, 5):  # IP, port, + timeout
                self._set_row_visible(row, True)
                
        elif connection_type == "Serial":
            # Show serial and common params
            for row in range(4, 7):  # Port, baud rate, + timeout
                self._set_row_visible(row, True)
    
    def _set_row_visible(self, row, visible):
        """Set visibility of a form row."""
        label_item = self.params_layout.itemAt(row, QFormLayout.LabelRole)
        if label_item:
            label_widget = label_item.widget()
            if label_widget:
                label_widget.setVisible(visible)
        
        field_item = self.params_layout.itemAt(row, QFormLayout.FieldRole)
        if field_item:
            field_widget = field_item.widget()
            if field_widget:
                field_widget.setVisible(visible)
    
    def _handle_connect(self):
        """Handle the connect button."""
        connection_type = self.conn_type.currentText()
        timeout = float(self.timeout.text()) if self.timeout.text() else 5.0
        
        try:
            if connection_type == "VISA":
                resource = self.visa_resource.text().strip()
                if not resource:
                    raise ValueError("Resource string is required")
                
                self.result_info = {
                    'connection_type': 'visa',
                    'resource': resource,
                    'timeout': timeout * 1000  # Convert to ms
                }
                
            elif connection_type == "TCP/IP":
                ip = self.ip_address.text().strip()
                port = int(self.ip_port.text()) if self.ip_port.text() else 5025
                
                if not ip:
                    raise ValueError("IP address is required")
                
                # Create TCPIP resource string
                resource = f"TCPIP::{ip}::{port}::SOCKET"
                
                self.result_info = {
                    'connection_type': 'socket',
                    'resource': resource,
                    'host': ip,
                    'port': port,
                    'timeout': timeout
                }
                
            elif connection_type == "Serial":
                port = self.serial_port.text().strip()
                baud = int(self.baud_rate.currentText())
                
                if not port:
                    raise ValueError("Serial port is required")
                
                # Create ASRL resource string
                resource = f"ASRL::{port}::INSTR"
                
                self.result_info = {
                    'connection_type': 'serial',
                    'resource': resource,
                    'port': port,
                    'baud': baud,
                    'timeout': timeout
                }
            
            # Add metadata for use in application
            self.result_info.update({
                'model': 'Unknown',
                'manufacturer': 'Unknown',
                'serial': 'N/A',
                'firmware': 'N/A'
            })
            
            self.accept()
            
        except ValueError as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Connection Error", str(e))