from typing import Dict, Optional, List, Any
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QDialog, QLabel,
    QProgressBar, QFrame
)
from PySide6.QtCore import Qt, Signal, Slot

from pymetr.ui.views.base import BaseWidget
from pymetr.core.logging import logger

class InstrumentTable(QTableWidget):
    """Table for displaying discovered instruments."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._instrument_data: List[Dict] = []
        
    def _setup_ui(self):
        """Configure table UI."""
        # Setup columns
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels([
            "Manufacturer",
            "Model",
            "Serial",
            "Firmware",
            "Resource"
        ])
        
        # Configure header
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        
        # Configure selection
        self.setSelectionBehavior(QTableWidget.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        
        # Style
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1E1E1E;
                alternate-background-color: #252525;
                color: #D4D4D4;
                gridline-color: #2D2D2D;
                selection-background-color: #264F78;
                selection-color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #2D2D2D;
                color: #FFFFFF;
                padding: 4px;
                border: none;
                border-right: 1px solid #3D3D3D;
            }
        """)
        
    def update_instruments(self, instruments: Dict[str, Dict]):
        """Update table with discovered instruments."""
        self.setRowCount(0)
        self._instrument_data.clear()
        
        for info in instruments.values():
            row = self.rowCount()
            self.insertRow(row)
            
            # Add instrument data
            self.setItem(row, 0, QTableWidgetItem(info.get('manufacturer', '')))
            self.setItem(row, 1, QTableWidgetItem(info.get('model', '')))
            self.setItem(row, 2, QTableWidgetItem(info.get('serial', '')))
            self.setItem(row, 3, QTableWidgetItem(info.get('firmware', '')))
            self.setItem(row, 4, QTableWidgetItem(info.get('resource', '')))
            
            # Store full info
            self._instrument_data.append(info)
            
    def get_selected_instrument(self) -> Optional[Dict]:
        """Get the currently selected instrument info."""
        row = self.currentRow()
        if row >= 0 and row < len(self._instrument_data):
            return self._instrument_data[row]
        return None

class DiscoveryDialog(QDialog):
    """Dialog for instrument discovery and connection."""
    
    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.result_info = None
        
        self._setup_ui()
        self._connect_signals()
        
        # Start discovery
        self.state.discover_instruments()
        
    def _setup_ui(self):
        """Initialize dialog UI."""
        self.setWindowTitle("Discover Instruments")
        self.setMinimumSize(800, 400)
        
        layout = QVBoxLayout(self)
        
        # Status section
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #2D2D2D;
                border-bottom: 1px solid #3D3D3D;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        status_layout = QHBoxLayout(status_frame)
        
        self.status_label = QLabel("Discovering instruments...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.progress_bar)
        layout.addWidget(status_frame)
        
        # Instrument table
        self.table = InstrumentTable()
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._handle_refresh)
        button_layout.addWidget(self.refresh_button)
        
        button_layout.addStretch()
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._handle_connect)
        button_layout.addWidget(self.connect_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def _connect_signals(self):
        """Connect to state signals."""
        self.state.discovery_started.connect(self._handle_discovery_started)
        self.state.discovery_complete.connect(self._handle_discovery_complete)
        self.state.instrument_found.connect(self._handle_instrument_found)
        
    @Slot()
    def _handle_discovery_started(self):
        """Handle start of discovery."""
        self.status_label.setText("Discovering instruments...")
        self.progress_bar.setMaximum(0)
        self.refresh_button.setEnabled(False)
        self.connect_button.setEnabled(False)
        
    @Slot(dict)
    def _handle_discovery_complete(self, instruments: Dict):
        """Handle discovery completion."""
        self.status_label.setText(f"Found {len(instruments)} instruments")
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(100)
        self.refresh_button.setEnabled(True)
        self.connect_button.setEnabled(True)
        self.table.update_instruments(instruments)
        
    @Slot(dict)
    def _handle_instrument_found(self, info: Dict):
        """Handle individual instrument discovery."""
        self.status_label.setText(f"Found {info.get('model', 'Unknown')}")
        
    def _handle_refresh(self):
        """Handle refresh button."""
        self.state.discover_instruments()
        
    def _handle_connect(self):
        """Handle connect button."""
        if info := self.table.get_selected_instrument():
            self.result_info = info
            self.accept()

class DiscoveryView(BaseWidget):
    """View for instrument discovery and management."""
    
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self._setup_ui()
        
        # Start discovery
        self.state.discover_instruments()
        
    def _setup_ui(self):
        """Initialize view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Control section
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #2D2D2D;
                border-bottom: 1px solid #3D3D3D;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        control_layout = QHBoxLayout(control_frame)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._handle_refresh)
        control_layout.addWidget(self.refresh_button)
        
        self.status_label = QLabel()
        control_layout.addWidget(self.status_label)
        
        control_layout.addStretch()
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._handle_connect)
        control_layout.addWidget(self.connect_button)
        
        layout.addWidget(control_frame)
        
        # Instrument table
        self.table = InstrumentTable()
        layout.addWidget(self.table)
        
    def _handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if prop == 'instruments':
            self.table.update_instruments(value)
            self.status_label.setText(f"Found {len(value)} instruments")
            
    @Slot()
    def _handle_refresh(self):
        """Handle refresh button."""
        self.state.discover_instruments()
        
    @Slot()
    def _handle_connect(self):
        """Handle connect button."""
        if info := self.table.get_selected_instrument():
            self.state.connect_instrument(info)