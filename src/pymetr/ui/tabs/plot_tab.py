# pymetr/views/tabs/plot_tab.py
from pathlib import Path
from typing import Optional, Any, Dict
from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QLabel, QSizePolicy, QDialog, 
    QFormLayout, QComboBox, QDoubleSpinBox, QPushButton, 
    QHBoxLayout, QLineEdit
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QAction, QIcon
import pyqtgraph as pg
import numpy as np

from pymetr.ui.tabs.base import BaseTab
from pymetr.ui.views.plot.plot_view import PlotView
from pymetr.core.logging import logger

class PlotTab(BaseTab):
    """
    Enhanced plot tab with ROI synchronization and efficient toolbar actions.
    """
    
    # Updated icon mapping for toolbar
    TOOLBAR_ICONS = {
        'autoscale': 'autoscale.png',
        'isolate': 'isolate.png',
        'group': 'group.png',
        'marker': 'markers.png',
        'cursor': 'cursor.png',
        'camera': 'camera.png',
        'save': 'save.png',
        'visibility': 'visibility_on.png',
        'traces': 'traces.png',
        'grid': 'grid.png',
        'roi': 'roi.png'
    }

    def __init__(self, state, model_id: str, parent=None):
        logger.debug(f"Initializing PlotTab for model_id: {model_id}")
        self.plot_view: Optional[PlotView] = None
        # Cache for toolbar actions
        self._toolbar_actions: Dict[str, QAction] = {}

        super().__init__(state, model_id, parent)
        
        # Connect to state signals for ROI sync if needed
        self.state.model_changed.connect(self._handle_model_changed)
        logger.debug("PlotTab initialized and connected to state")

    def _setup_ui(self):
        """Initialize the tab UI with enhanced toolbar."""
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create main plot view (now includes ROI plot)
        self.plot_view = PlotView(self.state, self._model_id, self)
        layout.addWidget(self.plot_view)

        # Setup enhanced toolbar
        self._setup_enhanced_toolbar()

    def _setup_enhanced_toolbar(self):
        """Setup enhanced toolbar with toggles and new actions."""
        self.toolbar.addButton("Auto Scale", self._get_icon('autoscale'), self._handle_auto_range)
        self.toolbar.addSeparator()
        
        grid_action = self.toolbar.addToggleButton("Toggle Grid", self._get_icon('grid'),
                                                    checked=True, callback=self._handle_grid_visibility)
        grid_action.setChecked(True)
        self._toolbar_actions['grid'] = grid_action
        
        roi_action = self.toolbar.addToggleButton("Toggle ROI", self._get_icon('roi'),
                                                checked=False, callback=self._handle_roi_visibility)
        roi_action.setChecked(False)
        self._toolbar_actions['roi'] = roi_action
        
        self.toolbar.addSeparator()
        
        self.toolbar.addButton("Group All Traces", self._get_icon('group'), self._handle_group_all_traces)
        self.toolbar.addButton("Isolate All Traces", self._get_icon('isolate'), self._handle_isolate_all_traces)
        
        self.toolbar.addSeparator()
        
        self.toolbar.addButton("Add Marker", self._get_icon('marker'), self._on_add_marker_clicked)
        self.toolbar.addButton("Add X Cursor", self._get_icon('cursor'), self._on_add_x_cursor_clicked)
        self.toolbar.addButton("Add Y Cursor", self._get_icon('cursor'), self._on_add_y_cursor_clicked)
        
        self.toolbar.addStretch()

    def _handle_grid_visibility(self, visible: bool):
        """Handle grid visibility toggle."""
        try:
            if self.model:
                self.model.set_property('grid_enabled', visible)
            if self.plot_view:
                self.plot_view.main_plot_item.showGrid(x=visible, y=visible, alpha=0.3)
                
        except Exception as e:
            logger.error(f"Error handling grid visibility: {e}")

    def _handle_group_all_traces(self):
        """Set all traces to group mode."""
        try:
            if not self.model:
                return
            self.model.begin_update()
            for trace in self.model.get_children():
                if hasattr(trace, 'model_type') and trace.model_type == 'Trace':
                    trace.set_property('mode', 'Group')
            self.model.end_update()
            
        except Exception as e:
            logger.error(f"Error grouping all traces: {e}")

    def _handle_isolate_all_traces(self):
        """Set all traces to isolate mode."""
        try:
            if not self.model:
                return
            self.model.begin_update()
            for trace in self.model.get_children():
                if hasattr(trace, 'model_type') and trace.model_type == 'Trace':
                    trace.set_property('mode', 'Isolate')
            self.model.end_update()
            
        except Exception as e:
            logger.error(f"Error isolating all traces: {e}")

    @Slot(str, str, str, object)
    def _handle_model_changed(self, model_id: str, model_type: str, prop: str, value: Any):
        """Handle model changes affecting ROI and grid toggle from the tab perspective."""
        try:
            if not self.model or model_id != self.model.id:
                return
            if prop == 'roi' and self.plot_view:
                self.plot_view.roi.setRegion(value)
            elif prop == 'roi_visible' and self.plot_view:
                self.plot_view.roi_plot_area.setVisible(value)
                if 'roi' in self._toolbar_actions:
                    self._toolbar_actions['roi'].setChecked(value)
            elif prop == 'grid_enabled' and 'grid' in self._toolbar_actions:
                self._toolbar_actions['grid'].setChecked(value)
                
        except Exception as e:
            logger.error(f"Error handling model change: {e}")

    def _handle_roi_visibility(self, visible: bool):
        """Handle ROI visibility toggle."""
        logger.debug(f"ROI visibility toggle triggered: {visible}")
        try:
            if self.plot_view:
                self.plot_view.roi_plot_area.setVisible(visible)
                self.plot_view._apply_roi_update() # Add RS
            if self.model:
                self.model.set_property('roi_visible', visible)
                logger.debug(f"Model property 'roi_visible' set to {visible}")
        except Exception as e:
            logger.error(f"Error in _handle_roi_visibility: {e}")

    def _handle_auto_range(self):
        """Handle auto range action efficiently."""
        try:
            if self.plot_view:
                self.plot_view._suppress_roi_updates = True
                self.plot_view.main_plot_item.autoRange()
                if self.plot_view.roi:
                    x_range = self.plot_view.main_plot_item.getViewBox().viewRange()[0]
                    self.plot_view.roi.setRegion(x_range)
                self.plot_view._suppress_roi_updates = False
                self.plot_view._apply_roi_update()
                
        except Exception as e:
            logger.error(f"Error in _handle_auto_range: {e}")

    def _on_add_marker_clicked(self):
        """Handle Add Marker button click with efficient trace lookup."""
        try:
            if not self.plot_view or not self.model:
                return

            visible_traces = [
                (curve.opts.get('name', 'Unnamed'), curve)
                for curve in self.plot_view.trace_handler.traces.items()
                if curve.isVisible()
            ]

            if not visible_traces:
                logger.warning("No visible traces available for marker placement")
                return

            dialog = MarkerDialog(visible_traces, self)
            if dialog.exec():
                trace, x_pos, label = dialog.get_values()
                data = trace.getData()
                if data[0].size > 0:
                    idx = np.searchsorted(data[0], x_pos)
                    if idx >= data[0].size:
                        idx = data[0].size - 1
                    y_val = data[1][idx]
                    
                    self.model.create_marker(
                        x=x_pos,
                        y=y_val,
                        label=label,
                        color="#FFFF00",
                        size=8,
                        symbol="o"
                    )
                
        except Exception as e:
            logger.error(f"Error in _on_add_marker_clicked: {e}")

    def _on_add_x_cursor_clicked(self):
        """Add X cursor at current view center."""
        try:
            if not self.plot_view or not self.model:
                return
                
            viewbox = self.plot_view.main_plot_item.getViewBox()
            x_range = viewbox.viewRange()[0]
            pos = (x_range[0] + x_range[1]) / 2.0
            
            self.model.create_cursor(
                axis="x",
                position=pos,
                color="#FFFF00",
                style="dash",
                width=1,
                visible=True
            )
            
        except Exception as e:
            logger.error(f"Error in _on_add_x_cursor_clicked: {e}")

    def _on_add_y_cursor_clicked(self):
        """Add Y cursor at current view center."""
        try:
            if not self.plot_view or not self.model:
                return
                
            viewbox = self.plot_view.main_plot_item.getViewBox()
            y_range = viewbox.viewRange()[1]
            pos = (y_range[0] + y_range[1]) / 2.0
            
            self.model.create_cursor(
                axis="y",
                position=pos,
                color="#FF00FF",
                style="dot",
                width=1,
                visible=True
            )
            
        except Exception as e:
            logger.error(f"Error in _on_add_y_cursor_clicked: {e}")

    def _get_icon(self, name: str) -> QIcon:
        """Get cached icon from the icons directory."""
        icon_file = self.TOOLBAR_ICONS.get(name)
        if icon_file:
            icon_path = str(Path(__file__).parent.parent / 'icons' / icon_file)
            return QIcon(icon_path)
        return QIcon()


class MarkerDialog(QDialog):
    """
    Enhanced dialog for marker creation with improved trace selection.
    """
    def __init__(self, traces, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Marker")
        self.setModal(True)

        layout = QFormLayout(self)
        layout.setSpacing(10)

        self.trace_combo = QComboBox()
        for name, trace in traces:
            self.trace_combo.addItem(name, trace)
        layout.addRow("Trace:", self.trace_combo)

        self.x_pos = QDoubleSpinBox()
        self.x_pos.setRange(-1e9, 1e9)
        self.x_pos.setDecimals(6)
        self.x_pos.setStepType(QDoubleSpinBox.AdaptiveDecimalStepType)
        self.x_pos.setButtonSymbols(QDoubleSpinBox.NoButtons)
        layout.addRow("X Position:", self.x_pos)

        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Enter marker label...")
        layout.addRow("Label:", self.label_input)

        btn_box = QWidget()
        btn_layout = QHBoxLayout(btn_box)
        btn_layout.setContentsMargins(0, 10, 0, 0)
        
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addRow(btn_box)

        self.x_pos.setFocus()

    def get_values(self):
        """Get dialog values with proper defaults."""
        trace = self.trace_combo.currentData()
        x_pos = self.x_pos.value()
        label = self.label_input.text() or f"Marker ({x_pos:.2f})"
        return trace, x_pos, label
