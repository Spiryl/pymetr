# views/widgets/table_view.py
from typing import Optional, Any
from PySide6.QtWidgets import (
    QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView
)
from PySide6.QtCore import Qt, Signal
import pandas as pd

from pymetr.views.widgets.base import BaseWidget
from pymetr.core.logging import logger

class TableView(BaseWidget):
    """Core widget for displaying data tables with sorting."""
    
    selection_changed = Signal(pd.DataFrame)  # Emitted when selection changes
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, parent)
        self._setup_ui()
        self.set_model(model_id)
        
    def _setup_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Table widget
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        
        # Configure header
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setDefaultSectionSize(100)
        header.setMinimumSectionSize(50)
        header.setStretchLastSection(True)
        
        # Set selection behavior
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        
        # Style
        self.table.setStyleSheet("""
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
        
        layout.addWidget(self.table)
        
        # Connect selection signal
        self.table.itemSelectionChanged.connect(self._handle_selection_changed)
            
    def _handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if prop == 'data':
            self._update_table(value)
            
    def _update_table(self, data: pd.DataFrame):
        """Update table with new data."""
        if not isinstance(data, pd.DataFrame):
            logger.error(f"Expected DataFrame, got {type(data)}")
            return
            
        try:
            # Clear table
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            
            # Set dimensions
            self.table.setRowCount(len(data))
            self.table.setColumnCount(len(data.columns))
            
            # Set headers
            self.table.setHorizontalHeaderLabels(data.columns.tolist())
            
            # Populate data
            for row_idx, (_, row) in enumerate(data.iterrows()):
                for col_idx, value in enumerate(row):
                    item = self._create_item(value)
                    self.table.setItem(row_idx, col_idx, item)
                    
        except Exception as e:
            logger.error(f"Error updating table: {e}")
            
    def _create_item(self, value: Any) -> QTableWidgetItem:
        """Create properly formatted table item."""
        item = QTableWidgetItem()
        
        if pd.isna(value):
            item.setText("")
            item.setData(Qt.DisplayRole, None)
        elif isinstance(value, (int, float)):
            if isinstance(value, float):
                # Format floats nicely
                text = f"{value:.6g}"
            else:
                text = str(value)
            item.setText(text)
            item.setData(Qt.DisplayRole, value)  # For proper sorting
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        elif isinstance(value, bool):
            item.setText(str(value))
            item.setData(Qt.DisplayRole, int(value))  # For sorting
            item.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        else:
            item.setText(str(value))
            item.setData(Qt.DisplayRole, str(value))
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Make read-only
        return item
        
    def _handle_selection_changed(self):
        """Emit selected data when selection changes."""
        if self.model:
            data = self.get_selected_data()
            self.selection_changed.emit(data)
        
    def get_selected_data(self) -> pd.DataFrame:
        """Get data from selected rows."""
        if not self.model:
            return pd.DataFrame()
            
        data = self.model.get_property('data')
        if not isinstance(data, pd.DataFrame):
            return pd.DataFrame()
            
        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))
        return data.iloc[selected_rows].copy()