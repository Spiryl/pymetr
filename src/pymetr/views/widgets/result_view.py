from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QFrame, QWidget
)
from PySide6.QtCore import Qt, Slot

from pymetr.views.widgets.base import BaseWidget
from pymetr.views.widgets.plot_view import PlotView
from pymetr.views.widgets.table_view import TableView
from pymetr.core.logging import logger

class ResultHeader(QFrame):
    """Header showing test result info and status."""
    
    STATUS_STYLES = {
        "Pass": {
            "color": "#2ECC71",
            "icon": "✅"
        },
        "Fail": {
            "color": "#E74C3C",
            "icon": "❌"
        },
        "Error": {
            "color": "#F1C40F",
            "icon": "⚠️"
        },
        "Running": {
            "color": "#3498DB",
            "icon": "🔄"
        },
        "Not Run": {
            "color": "#95A5A6",
            "icon": "⭕"
        }
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
    def _setup_ui(self):
        """Initialize header UI."""
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D2D;
                border-bottom: 1px solid #3D3D3D;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.name_label)
        
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #95A5A6;")
        layout.addWidget(self.info_label)
        
        layout.addStretch()
        
    def update_name(self, name: str):
        """Update test name."""
        self.name_label.setText(name)
        
    def update_status(self, status: str):
        """Update test status with proper styling."""
        style = self.STATUS_STYLES.get(status, self.STATUS_STYLES["Not Run"])
        self.status_label.setStyleSheet(f"color: {style['color']}; font-size: 13px;")
        self.status_label.setText(f"{style['icon']} {status}")
        
    def update_info(self, info: str):
        """Update additional info display."""
        self.info_label.setText(info)

class ResultView(BaseWidget):
    """
    Widget for displaying test results including:
    - Test status and info
    - Plot visualization
    - Data tables
    """
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, parent)
        
        # Track child views
        self.plot_view: Optional[PlotView] = None
        self.table_view: Optional[TableView] = None
        
        # Set up UI before setting model
        self._setup_ui()
        
        # Set model and load content
        self.set_model(model_id)
        
    def _setup_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        self.header = ResultHeader()
        layout.addWidget(self.header)
        
        # Content splitter
        self.content_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(self.content_splitter)
        
    def _handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if prop == 'name':
            self.header.update_name(value)
        elif prop == 'status':
            self.header.update_status(value)
            
    def _handle_child_added(self, child_id: str, child_model):
        """Handle child model addition."""
        model_type = type(child_model).__name__
        
        if model_type == 'Plot' and not self.plot_view:
            # Create plot view
            self.plot_view = PlotView(self.state, child_id, self)
            self.content_splitter.insertWidget(0, self.plot_view)
            
        elif model_type == 'DataTable' and not self.table_view:
            # Create table view
            self.table_view = TableView(self.state, child_id, self)
            self.content_splitter.addWidget(self.table_view)
            
        # Set initial splitter sizes if both views exist
        if self.plot_view and self.table_view:
            self.content_splitter.setSizes([600, 400])
            
    def _update_header_info(self):
        """Update header info from model state."""
        if not self.model:
            return
            
        # Update test info
        info_parts = []
        
        # Add timestamp if available
        if created_time := self.model.get_property('created_time'):
            info_parts.append(f"Created: {created_time.strftime('%H:%M:%S')}")
            
        # Add execution time if available
        if exec_time := self.model.get_property('execution_time'):
            info_parts.append(f"Time: {exec_time:.1f}s")
            
        # Add measurements summary if available
        if measurements := self.model.get_property('measurements'):
            passed = sum(1 for m in measurements if m.get('pass_fail', True))
            total = len(measurements)
            info_parts.append(f"Measurements: {passed}/{total}")
            
        self.header.update_info(" | ".join(info_parts))
        
    def update_layout(self):
        """Update layout based on visible components."""
        if self.plot_view:
            self.plot_view.setVisible(self.plot_view.model is not None)
            
        if self.table_view:
            self.table_view.setVisible(self.table_view.model is not None)
            
        # Update splitter sizes
        visible_widgets = []
        if self.plot_view and self.plot_view.isVisible():
            visible_widgets.append(self.plot_view)
        if self.table_view and self.table_view.isVisible():
            visible_widgets.append(self.table_view)
            
        if len(visible_widgets) == 2:
            self.content_splitter.setSizes([600, 400])