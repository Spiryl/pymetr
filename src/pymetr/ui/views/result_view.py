# views/widgets/result_view.py
from enum import Enum, auto
from typing import Any
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QFrame,
    QLabel, QScrollArea, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt
from pymetr.ui.views.base import BaseWidget
from pymetr.ui.views.plot.plot_view import PlotView
from pymetr.ui.views.table_view import TableView
from pymetr.models.plot import Plot
from pymetr.models.table import DataTable
from pymetr.models.measurement import Measurement
from pymetr.core.logging import logger


class ResultHeader(QFrame):
    """Header showing result name and status."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Name label (left-aligned, bold)
        self.name_label = QLabel()
        layout.addWidget(self.name_label)
        
        layout.addStretch()
        
        # Status label (right-aligned)
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
    def update_name(self, name: str):
        self.name_label.setText(name)
        
    def update_status(self, status: str):
        """Update status with appropriate color."""
        color = {
            'Passed': '#4EC9B0',  # Green
            'Failed': '#F14C4C',  # Red
            'Running': '#CCCCCC', # Light gray
            'Pending': '#CCCCCC'  # Light gray
        }.get(status, '#CCCCCC')
        
        self.status_label.setStyleSheet(f"""
            font-size: 12px;
            color: {color};
            font-weight: bold;
        """)
        self.status_label.setText(status)


class MeasurementWidget(QFrame):
    """Widget for displaying a single measurement."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: #252525;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
            }
            QLabel {
                color: #FFFFFF;
            }
        """)
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.name_label)
        
        self.value_label = QLabel()
        self.value_label.setStyleSheet("font-size: 16px;")
        layout.addWidget(self.value_label)
        
    def update_measurement(self, measurement: Measurement):
        self.name_label.setText(measurement.name)
        self.value_label.setText(f"{measurement.value} {measurement.units}")
        
        # Update color based on limits if set
        if hasattr(measurement, 'min_val') and hasattr(measurement, 'max_val'):
            if measurement.value < measurement.min_val or measurement.value > measurement.max_val:
                self.value_label.setStyleSheet("font-size: 16px; color: #F14C4C;")
            else:
                self.value_label.setStyleSheet("font-size: 16px; color: #4EC9B0;")


class LayoutMode(Enum):
    """Available layout modes for result content."""
    Vertical = auto()      # Stack everything vertically
    Grid2 = auto()         # 2 columns
    Grid3 = auto()         # 3 columns
    GridAuto = auto()      # Auto-adjust columns based on window width


class ResultView(BaseWidget):
    def __init__(self, state, model_id: str, parent=None):
        logger.debug(f"Initializing ResultView for model_id: {model_id}")
        super().__init__(state, parent)
        self._signals_connected = False
        
        self.child_views = {}
        self.layout_mode = LayoutMode.GridAuto
        
        # Ensure the main widget expands in both directions
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(400, 300)
        
        self._init_ui()
        self.set_model(model_id)
        
    def _init_ui(self):
        """Initialize the UI components with improved layout behavior."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header setup remains the same
        self.header = ResultHeader()
        self.header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.header.setMinimumHeight(20)
        layout.addWidget(self.header)
        
        # Scroll area with improved size policy
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: #1E1E1E;
                border: none;
            }
        """)
        layout.addWidget(self.scroll_area)
        
        # Content widget with improved layout handling
        self.content_widget = QWidget()
        self.content_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.scroll_area.setWidget(self.content_widget)
        
        self.content_layout = QGridLayout(self.content_widget)
        self.content_layout.setContentsMargins(4, 0, 4, 4)
        self.content_layout.setSpacing(4)
        
        # Critical: Set the content layout to expand properly
        self.content_layout.setColumnStretch(0, 1)
        self.content_layout.setRowStretch(0, 1)
    
    def set_model(self, model_id: str):
        """Set up model and establish connections."""
        super().set_model(model_id)
        if not self.model:
            return
            
        # Update header
        name = self.model.get_property('name', 'Untitled Result')
        status = self.model.get_property('status', None)
        self.header.update_name(name)
        self.header.update_status(status)
        
        # Connect signals only once
        if not self._signals_connected:
            self.state.model_changed.connect(self._handle_model_changed)
            self.state.models_linked.connect(self._handle_models_linked)
            self._signals_connected = True
        
        # Add existing children
        for child in self.model.get_children():
            self._add_child_view(child, force_layout=False)
        
        # Update layout once after all children are added
        self._update_layout()
    
    def _add_child_view(self, model, force_layout=True):
        """Add child view with improved size handling."""
        if model.id in self.child_views:
            return
            
        view = None
        try:
            if isinstance(model, Plot):
                view = PlotView(self.state, model.id, self)
                view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                view.setMinimumSize(300, 250)
            elif isinstance(model, DataTable):
                view = TableView(self.state, model.id, self)
                view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                view.setMinimumHeight(200)
            elif isinstance(model, Measurement):
                view = MeasurementWidget(self)
                view.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
                view.setMinimumHeight(80)
                view.update_measurement(model)
                
            if view:
                self.child_views[model.id] = view
                if force_layout:
                    self._update_layout()
                    
        except Exception as e:
            logger.error(f"Error creating view for {model.id}: {e}")
    
    def _update_layout(self):
        """Enhanced layout management for better space utilization."""
        # Clear existing layout and reset stretch factors
        for i in range(self.content_layout.rowCount()):
            self.content_layout.setRowStretch(i, 0)
        for i in range(self.content_layout.columnCount()):
            self.content_layout.setColumnStretch(i, 0)
            
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        
        views = list(self.child_views.values())
        if not views:
            # Even with no views, ensure the layout stretches
            self.content_layout.setRowStretch(0, 1)
            self.content_layout.setColumnStretch(0, 1)
            return
            
        # Calculate grid dimensions
        viewport_width = self.scroll_area.viewport().width()
        viewport_height = self.scroll_area.viewport().height()
        width = self.width()
        
        # Determine columns based on layout mode
        if self.layout_mode == LayoutMode.GridAuto:
            cols = 1 if width < 800 else (2 if width < 1200 else 3)
        elif self.layout_mode == LayoutMode.Grid2:
            cols = 2
        elif self.layout_mode == LayoutMode.Grid3:
            cols = 3
        else:  # LayoutMode.Vertical
            cols = 1
            
        rows = (len(views) + cols - 1) // cols
        
        # Ensure at least one row and column
        rows = max(1, rows)
        cols = max(1, cols)
        
        # Set up grid stretching
        available_height = viewport_height - (rows - 1) * self.content_layout.spacing()
        row_height = available_height // rows if rows > 0 else available_height
        
        # Special handling for single items
        if len(views) == 1:
            view = views[0]
            if isinstance(view, (PlotView, TableView)):
                view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                if isinstance(view, PlotView):
                    view.setMinimumHeight(max(250, viewport_height - 40))
            self.content_layout.addWidget(view, 0, 0, 1, cols)
            self.content_layout.setRowStretch(0, 1)
            for col in range(cols):
                self.content_layout.setColumnStretch(col, 1)
            return
            
        # For multiple items, set equal stretching
        for row in range(rows):
            self.content_layout.setRowStretch(row, 1)
        for col in range(cols):
            self.content_layout.setColumnStretch(col, 1)
        
        # Handle multiple items
        for idx, view in enumerate(views):
            row = idx // cols
            col = idx % cols
            
            # Ensure proper size policies
            if isinstance(view, (PlotView, TableView)):
                view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                if isinstance(view, PlotView):
                    view.setMinimumHeight(max(200, row_height))
                
            # Add widget to grid with proper span
            if idx == len(views) - 1 and len(views) % cols != 0:
                # Last item spans remaining columns if needed
                remaining_cols = cols - (len(views) % cols) + 1
                self.content_layout.addWidget(view, row, col, 1, remaining_cols)
            else:
                self.content_layout.addWidget(view, row, col)
        
        # Update content widget constraints
        self.content_widget.setMinimumWidth(viewport_width)
        self.content_widget.setMinimumHeight(viewport_height)
        
    def resizeEvent(self, event):
        """Enhanced resize handling."""
        super().resizeEvent(event)
        viewport = self.scroll_area.viewport()
        
        # Update content widget constraints
        self.content_widget.setMinimumWidth(viewport.width())
        
        # Trigger layout update if in auto mode
        if self.layout_mode == LayoutMode.GridAuto:
            self._update_layout()
    
    def set_layout_mode(self, mode: LayoutMode):
        """Change how content is arranged."""
        logger.debug(f"Setting layout mode to: {mode}")
        if mode != self.layout_mode:
            self.layout_mode = mode
            self._update_layout()
    
    def _handle_models_linked(self, parent_id: str, child_id: str):
        """Handle new model relationships."""
        if not self.model or parent_id != self.model.id:
            return
            
        # Only add view if we don't already have it
        if child_id not in self.child_views:
            child = self.state.get_model(child_id)
            if child:
                self._add_child_view(child)
    
    def _handle_model_changed(self, model_id: str, prop: str, value: Any):
        """Handle model property changes."""
        if not self.model:
            return
            
        # Handle parent model changes
        if model_id == self.model.id:
            if prop == 'name':
                self.header.update_name(value)
            elif prop == 'status':
                self.header.update_status(value)
            return
            
        # Handle child model changes
        view = self.child_views.get(model_id)
        if not view:
            return
            
        if hasattr(view, 'handle_property_update'):
            view.handle_property_update(prop, value)
        elif isinstance(view, MeasurementWidget):
            child_model = self.state.get_model(model_id)
            if child_model:
                view.update_measurement(child_model)
    
    def cleanup(self):
        """Clean up signal connections and resources."""
        if self._signals_connected and self.state:
            try:
                self.state.model_changed.disconnect(self._handle_model_changed)
                self.state.models_linked.disconnect(self._handle_models_linked)
            except:
                pass  # Ignore if already disconnected
            self._signals_connected = False
        
        # Clean up child views
        for view in self.child_views.values():
            if hasattr(view, 'cleanup'):
                view.cleanup()
        self.child_views.clear()
        
        super().cleanup()
