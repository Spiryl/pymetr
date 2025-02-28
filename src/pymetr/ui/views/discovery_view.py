from typing import Dict, Optional, List, Any
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel,
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


class DiscoveryView(BaseWidget):
    """Reusable view for instrument discovery and management."""
    
    # Signals 
    refresh_clicked = Signal()
    connect_clicked = Signal(dict)  # Emits selected instrument info
    
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        self._setup_ui()
        self._connect_signals()
        
    def _setup_ui(self):
        """Initialize view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Status section
        self.status_frame = QFrame()
        status_layout = QHBoxLayout(self.status_frame)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self._handle_refresh)
        status_layout.addWidget(self.refresh_button)
        
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        status_layout.addWidget(self.progress_bar)
        
        status_layout.addStretch()
        
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self._handle_connect)
        status_layout.addWidget(self.connect_button)
        
        layout.addWidget(self.status_frame)
        
        # Instrument table
        self.table = InstrumentTable()
        layout.addWidget(self.table, 1)  # Give the table extra space
    
    def _connect_signals(self):
        """Connect to state signals for discovery updates."""
        self.state.discovery_started.connect(self._handle_discovery_started)
        self.state.discovery_complete.connect(self._handle_discovery_complete)
        self.state.instrument_found.connect(self._handle_instrument_found)
        
    def update_instruments(self, instruments: Dict[str, Dict]):
        """Update the instrument table."""
        self.table.update_instruments(instruments)
        
    def get_selected_instrument(self) -> Optional[Dict]:
        """Get the currently selected instrument."""
        return self.table.get_selected_instrument()
        
    @Slot()
    def _handle_discovery_started(self):
        """Handle start of discovery."""
        self.status_label.setText("Discovering instruments...")
        self.progress_bar.setMaximum(0)  # Indeterminate
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
        
    @Slot()
    def _handle_refresh(self):
        """Handle refresh button click."""
        self.refresh_clicked.emit()
        
    @Slot()
    def _handle_connect(self):
        """Handle connect button click."""
        if info := self.table.get_selected_instrument():
            self.connect_clicked.emit(info)