# views/tabs/table_tab.py
from PySide6.QtWidgets import (
    QVBoxLayout, QToolBar, QStatusBar, QFileDialog,
    QMessageBox
)
from typing import Optional, List, Any
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, Slot

import pandas as pd

from pymetr.views.tabs.base import BaseTab
from pymetr.views.widgets.table_view import TableView
from pymetr.core.logging import logger

class TableTab(BaseTab):
    """Full-featured table tab with toolbar and export functionality."""
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, model_id, parent)
        self._setup_ui()
        self.set_model(model_id)

    def _setup_ui(self):
        """Initialize the tab UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        self.toolbar = QToolBar()
        layout.addWidget(self.toolbar)
        self._setup_toolbar()

        # Table view
        self.table_view = TableView(self.state, self.model_id, self)
        layout.addWidget(self.table_view)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #007ACC;
                color: white;
            }
        """)
        layout.addWidget(self.status_bar)
        
        # Connect to table view signals
        self.table_view.selection_changed.connect(self._handle_selection_changed)

    def _setup_toolbar(self):
        """Setup toolbar actions."""
        # Export actions
        export_menu = self.toolbar.addMenu("Export")
        
        self.export_csv_action = QAction("Export CSV...", self)
        self.export_csv_action.triggered.connect(lambda: self._handle_export('csv'))
        export_menu.addAction(self.export_csv_action)
        
        self.export_excel_action = QAction("Export Excel...", self)
        self.export_excel_action.triggered.connect(lambda: self._handle_export('excel'))
        export_menu.addAction(self.export_excel_action)
        
        self.export_json_action = QAction("Export JSON...", self)
        self.export_json_action.triggered.connect(lambda: self._handle_export('json'))
        export_menu.addAction(self.export_json_action)

    def _handle_export(self, format: str):
        """Handle export action."""
        if not self.model:
            return
            
        data = self.model.get_property('data')
        if not isinstance(data, pd.DataFrame) or data.empty:
            QMessageBox.warning(self, "Export Error", "No data to export")
            return
            
        # Get file name
        file_filters = {
            'csv': "CSV Files (*.csv)",
            'excel': "Excel Files (*.xlsx)",
            'json': "JSON Files (*.json)"
        }
        
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Data", "", file_filters[format]
        )
        
        if not file_name:
            return
            
        try:
            if format == 'csv':
                data.to_csv(file_name, index=False)
            elif format == 'excel':
                data.to_excel(file_name, index=False)
            elif format == 'json':
                data.to_json(file_name, orient='records')
                
            self.status_bar.showMessage(f"Data exported to {file_name}")
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            self.status_bar.showMessage(f"Error exporting data: {str(e)}")
            QMessageBox.critical(self, "Export Error", str(e))

    def _handle_selection_changed(self, selected_data: pd.DataFrame):
        """Update status bar with selection info."""
        if not selected_data.empty:
            self.status_bar.showMessage(
                f"Selected {len(selected_data)} of {len(self.model.get_property('data'))} rows"
            )
        else:
            self.status_bar.showMessage(
                f"Total rows: {len(self.model.get_property('data'))}"
            )

    def _handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if prop == 'data':
            row_count = len(value) if isinstance(value, pd.DataFrame) else 0
            self.status_bar.showMessage(f"Total rows: {row_count}")