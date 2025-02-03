from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, 
    QTableWidgetItem, QPushButton, QDialogButtonBox, QComboBox, 
    QLabel, QHeaderView)
from PySide6.QtCore import Qt
import logging

from pymetr.drivers.base import Instrument
from pymetr.drivers.registry import get_driver_info

logger = logging.getLogger(__name__)

class InstrumentDiscoveryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Discover Instruments")
        self.setModal(True)
        self.resize(800, 400)
        
        self.selected_instrument = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Click Refresh to start instrument discovery...")
        layout.addWidget(self.status_label)
        
        # Instrument table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Manufacturer", "Model", "Serial", "Firmware", "Resource"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)
        
        # QHeaderView resize mode is an enum in PySide6
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # Buttons
        button_box = QDialogButtonBox()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_instruments)
        button_box.addButton(refresh_btn, QDialogButtonBox.ActionRole)
        
        button_box.addButton(QDialogButtonBox.Ok)
        button_box.addButton(QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def refresh_instruments(self):
        """Use Instrument.list_instruments() to discover available devices."""
        self.table.setRowCount(0)
        self.status_label.setText("Discovering instruments...")
        self.repaint()  # Force UI update
        
        try:
            # Use the Instrument class's discovery method
            instruments = Instrument.list_instruments()
            
            for unique_id, info in instruments.items():
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                # Add instrument information to table
                self.table.setItem(row, 0, QTableWidgetItem(info['manufacturer']))
                self.table.setItem(row, 1, QTableWidgetItem(info['model']))
                self.table.setItem(row, 2, QTableWidgetItem(info['serial']))
                self.table.setItem(row, 3, QTableWidgetItem(info['firmware']))
                self.table.setItem(row, 4, QTableWidgetItem(info['resource']))
            
            self.status_label.setText(f"Found {self.table.rowCount()} instruments")
            
        except Exception as e:
            logger.error(f"Error discovering instruments: {e}")
            self.status_label.setText(f"Error during discovery: {str(e)}")
            
    def accept(self):
        """Handle OK button click."""
        current_row = self.table.currentRow()
        if current_row >= 0:
            # Gather selected instrument information
            self.selected_instrument = {
                'manufacturer': self.table.item(current_row, 0).text(),
                'model': self.table.item(current_row, 1).text(),
                'serial': self.table.item(current_row, 2).text(),
                'firmware': self.table.item(current_row, 3).text(),
                'resource': self.table.item(current_row, 4).text()
            }
            
            try:
                # Check if we have a driver for this model
                driver_info = get_driver_info(self.selected_instrument['model'])
                self.selected_instrument['driver_info'] = driver_info
                super().accept()
            except ValueError as e:
                logger.error(f"No driver found: {e}")
                self.status_label.setText(f"No driver found for {self.selected_instrument['model']}")
        else:
            self.status_label.setText("Please select an instrument")