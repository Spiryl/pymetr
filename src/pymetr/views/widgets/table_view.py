from typing import Optional, Any
from PySide6.QtWidgets import (
    QVBoxLayout, QTableWidget, QTableWidgetItem, 
    QHeaderView, QStatusBar
)
from PySide6.QtCore import Qt, Slot
import pandas as pd
import numpy as np

from pymetr.views.widgets.base import BaseWidget
from pymetr.core.logging import logger

class TableView(BaseWidget):
    """
    Widget for displaying data tables with filtering and sorting.
    Handles large datasets efficiently and maintains column formatting.
    """
    
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
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #007ACC;
                color: white;
            }
        """)
        layout.addWidget(self.status_bar)
        
    def _handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if prop == 'data':
            self._update_table(value)
        elif prop == 'filter':
            self._apply_filter(value)
        elif prop == 'sort':
            self._apply_sort(value)
            
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
                    
            # Update status
            self.status_bar.showMessage(f"Loaded {len(data)} rows, {len(data.columns)} columns")
            
        except Exception as e:
            logger.error(f"Error updating table: {e}")
            self.status_bar.showMessage(f"Error updating table: {str(e)}")
            
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
        
    def _apply_filter(self, filter_spec: dict):
        """Apply filtering to the table."""
        # Future: Implement filtering
        pass
        
    def _apply_sort(self, sort_spec: dict):
        """Apply sorting to the table."""
        # Future: Implement sorting
        pass
        
    def get_selected_data(self) -> pd.DataFrame:
        """Get data from selected rows."""
        if not self.model:
            return pd.DataFrame()
            
        data = self.model.get_property('data')
        if not isinstance(data, pd.DataFrame):
            return pd.DataFrame()
            
        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))
        return data.iloc[selected_rows].copy()
        
    def export_data(self, path: str, format: str = 'csv'):
        """Export table data to file."""
        if not self.model:
            return
            
        data = self.model.get_property('data')
        if not isinstance(data, pd.DataFrame):
            return
            
        try:
            if format.lower() == 'csv':
                data.to_csv(path, index=False)
            elif format.lower() == 'excel':
                data.to_excel(path, index=False)
            elif format.lower() == 'json':
                data.to_json(path, orient='records')
            else:
                raise ValueError(f"Unsupported format: {format}")
                
            self.status_bar.showMessage(f"Data exported to {path}")
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            self.status_bar.showMessage(f"Error exporting data: {str(e)}")