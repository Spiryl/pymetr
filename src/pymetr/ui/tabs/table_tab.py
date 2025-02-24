from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QMessageBox, QInputDialog,
    QDialog, QLabel, QLineEdit, QDialogButtonBox, QFormLayout,
    QFileDialog
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt, Slot, Signal
import pandas as pd
import numpy as np
from typing import Any

from pymetr.ui.tabs.base import BaseTab
from pymetr.ui.views.table_view import TableView
from pymetr.core.logging import logger
from pymetr.ui.tabs.toolbar import TabToolbar

class FilterDialog(QDialog):
    """Dialog for creating column filters."""
    def __init__(self, columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Filter Data")
        self.columns = columns
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QFormLayout(self)
        
        # Column selection
        self.column_edit = QLineEdit()
        self.column_edit.setPlaceholderText("Column name")
        layout.addRow("Column:", self.column_edit)
        
        # Condition input
        self.condition_edit = QLineEdit()
        self.condition_edit.setPlaceholderText("e.g. > 0, == 'value', etc.")
        layout.addRow("Condition:", self.condition_edit)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_filter(self):
        return (self.column_edit.text(), self.condition_edit.text())

class TableTab(BaseTab):
    """Enhanced table tab with advanced features."""
    
    data_changed = Signal(pd.DataFrame)  # Emitted when data changes
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, model_id, parent)
        self._filters = []  # Store active filters
        
    def _setup_ui(self):
        """Initialize the tab UI components."""
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Table view
        self.table_view = TableView(self.state, self.model_id, self)
        
        # Set up toolbar actions
        self._setup_toolbar_actions()
        
        # Add widgets to layout
        layout.addWidget(self.table_view)
        
        # Connect signals
        self.table_view.selection_changed.connect(self._handle_selection_changed)
        
    def _setup_toolbar_actions(self):
        """Set up toolbar actions and menus."""
        # Export menu
        export_menu = self.toolbar.addDropdown("Export")
        
        # Export actions
        export_menu.addAction("CSV...").triggered.connect(
            lambda: self._handle_export('csv')
        )
        export_menu.addAction("Excel...").triggered.connect(
            lambda: self._handle_export('excel')
        )
        export_menu.addAction("JSON...").triggered.connect(
            lambda: self._handle_export('json')
        )
        
        self.toolbar.addSeparator()
        
        # Filter menu
        filter_menu = self.toolbar.addDropdown("Filter")
        filter_menu.addAction("Add Filter...").triggered.connect(self._add_filter)
        filter_menu.addAction("Clear Filters").triggered.connect(self._clear_filters)
        
        # Statistics menu
        stats_menu = self.toolbar.addDropdown("Statistics")
        stats_menu.addAction("Summary Statistics").triggered.connect(
            self._show_summary_stats
        )
        stats_menu.addAction("Correlation Matrix").triggered.connect(
            self._show_correlation_matrix
        )
        
        # Add stretcher at the end
        self.toolbar.addStretch()
        
    def set_model(self, model_id: str):
        """Override to ensure TableView gets model updates."""
        logger.debug(f"TableTab.set_model called with {model_id}")
        super().set_model(model_id)
        if hasattr(self, 'table_view'):
            logger.debug("Setting model on table_view")
            self.table_view.set_model(model_id)
            if self.model:
                data = self.model.get_property('data')
                if isinstance(data, pd.DataFrame):
                    logger.debug(f"Initial data update: {len(data)} rows")
                    self.table_view._update_table(data)
                    self._update_status(data)

    def handle_property_update(self, prop: str, value: Any):
        """Handle property updates from the model."""
        logger.debug(f"TableTab.handle_property_update: {prop}")
        if prop == 'data' and hasattr(self, 'table_view'):
            logger.debug(f"Updating table with {len(value)} rows")
            self.table_view._update_table(value)
            self._update_status(value)
                    
    def _update_status(self, data: pd.DataFrame):
        """Update status bar with current data info."""
        if isinstance(data, pd.DataFrame):
            total = len(data)
            selected = len(self.table_view.get_selected_data())
            memory = data.memory_usage(deep=True).sum()
            memory_str = self._format_memory(memory)
            
            msg = f"Total rows: {total:,}  |  Selected: {selected:,}  |  Memory usage: {memory_str}"
            self.state.set_status(msg)
            
    def _format_memory(self, bytes: int) -> str:
        """Format memory size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024
        return f"{bytes:.1f} TB"
    
    def _handle_selection_changed(self, selected_data: pd.DataFrame):
        """Update status when selection changes."""
        if self.model:
            data = self.model.get_property('data')
            self._update_status(data)
            
    def _handle_export(self, format: str):
        """Handle data export to various formats."""
        if not self.model:
            return
            
        data = self.model.get_property('data')
        if not isinstance(data, pd.DataFrame) or data.empty:
            self.state.set_warning("No data to export")
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
                
            self.state.set_info(f"Data exported to {file_name}")
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            self.state.set_error(f"Error exporting data: {str(e)}")
            
    def _add_filter(self):
        """Add a new filter to the data."""
        if not self.model:
            return
            
        data = self.model.get_property('data')
        if not isinstance(data, pd.DataFrame) or data.empty:
            return
            
        dialog = FilterDialog(data.columns, self)
        if dialog.exec_():
            column, condition = dialog.get_filter()
            if column in data.columns:
                try:
                    # Create filter string
                    filter_str = f"data['{column}'] {condition}"
                    # Test filter
                    filtered = data[eval(filter_str)]
                    # If successful, add to filters
                    self._filters.append((column, condition))
                    # Apply all filters
                    self._apply_filters()
                    self.state.set_info(f"Filter added: {column} {condition}")
                except Exception as e:
                    self.state.set_error(f"Filter error: {str(e)}")
            else:
                self.state.set_warning(f"Column '{column}' not found")
                
    def _clear_filters(self):
        """Remove all filters and restore original data."""
        if self._filters:
            self._filters.clear()
            if self.model:
                data = self.model.get_property('data')
                if isinstance(data, pd.DataFrame):
                    self.table_view._update_table(data)
                    self._update_status(data)
                    self.state.set_info("All filters cleared")
                    
    def _apply_filters(self):
        """Apply all active filters to the data."""
        if not self.model or not self._filters:
            return
            
        data = self.model.get_property('data')
        if not isinstance(data, pd.DataFrame) or data.empty:
            return
            
        try:
            filtered_data = data.copy()
            for column, condition in self._filters:
                filter_str = f"filtered_data['{column}'] {condition}"
                filtered_data = filtered_data[eval(filter_str)]
                
            self.table_view._update_table(filtered_data)
            self._update_status(filtered_data)
            self.state.set_info(f"Applied {len(self._filters)} filter(s)")
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            self.state.set_error(f"Error applying filters: {str(e)}")
            
    def _show_summary_stats(self):
        """Show summary statistics for numeric columns."""
        if not self.model:
            return
            
        data = self.model.get_property('data')
        if not isinstance(data, pd.DataFrame) or data.empty:
            return
            
        # Create summary table
        numeric_data = data.select_dtypes(include=[np.number])
        if not numeric_data.empty:
            summary = numeric_data.describe()
            
            # Create new table model
            summary_table = self.state.create_model(
                type(self.model),
                title="Summary Statistics"
            )
            summary_table.set_property('data', summary)
            
            # Show in new tab
            self.state.register_model(summary_table)
            self.state.set_active_model(summary_table.id)
            self.state.set_info("Created summary statistics table")
        else:
            self.state.set_warning("No numeric columns found for statistics")
            
    def _show_correlation_matrix(self):
        """Show correlation matrix for numeric columns."""
        if not self.model:
            return
            
        data = self.model.get_property('data')
        if not isinstance(data, pd.DataFrame) or data.empty:
            return
            
        # Create correlation matrix
        numeric_data = data.select_dtypes(include=[np.number])
        if not numeric_data.empty:
            corr = numeric_data.corr()
            
            # Create new table model
            corr_table = self.state.create_model(
                type(self.model),
                title="Correlation Matrix"
            )
            corr_table.set_property('data', corr)
            
            # Show in new tab
            self.state.register_model(corr_table)
            self.state.set_active_model(corr_table.id)
            self.state.set_info("Created correlation matrix")
        else:
            self.state.set_warning("No numeric columns found for correlation")