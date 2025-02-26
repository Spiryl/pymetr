from pathlib import Path
from typing import Optional, Any, Dict, List, Type
from PySide6.QtWidgets import (
    QVBoxLayout, QWidget, QLabel, QSizePolicy, QDialog, 
    QFormLayout, QComboBox, QDoubleSpinBox, QPushButton, 
    QHBoxLayout, QLineEdit, QMenu, QToolButton
)
from PySide6.QtCore import Qt, Slot, Signal
from PySide6.QtGui import QIcon, QAction
import pyqtgraph as pg
import numpy as np

from pymetr.ui.tabs.base import BaseTab
from pymetr.ui.views.plot.plot_view import PlotView
from pymetr.core.logging import logger
from pymetr.models.analysis import (
    Analysis, RiseTime, FallTime, PulseWidth, PhaseDifference, 
    SlewRate, DutyCycle, Overshoot, Jitter, EyeDiagram,
    FFT, PeriodMeasurement, PeakToPeak
)

class AnalysisDialog(QDialog):
    """
    Dialog for configuring and creating analysis objects.
    """
    def __init__(self, analysis_class: Type[Analysis], traces: List[tuple], parent=None):
        super().__init__(parent)
        self.analysis_class = analysis_class
        self.traces = traces  # List of (trace_name, trace_obj) tuples
        self.result = None
        
        self.setWindowTitle(f"Configure {analysis_class.__name__}")
        self.setModal(True)
        
        # Create layout
        layout = QFormLayout(self)
        
        # Add input trace selection
        self.trace_combo = QComboBox()
        for name, _ in traces:
            self.trace_combo.addItem(name)
        layout.addRow("Input Trace:", self.trace_combo)
        
        # Add analysis-specific fields based on class
        self._setup_analysis_fields(layout)
        
        # Button box
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Create")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addRow("", button_layout)
    
    def _setup_analysis_fields(self, layout: QFormLayout):
        """Add analysis-specific configuration fields."""
        self.config = {}
        
        # Common field: analysis name
        self.name_edit = QLineEdit(self.analysis_class.__name__)
        layout.addRow("Analysis Name:", self.name_edit)
        
        # Analysis-specific fields
        if self.analysis_class in (RiseTime, FallTime, SlewRate):
            # Edge measurements
            edge_type = "rise" if self.analysis_class is RiseTime else "fall"
            self.config['edge_type'] = edge_type
        
        elif self.analysis_class is PhaseDifference:
            # Phase measurement needs reference trace
            self.ref_trace_combo = QComboBox()
            for name, _ in self.traces:
                self.ref_trace_combo.addItem(name)
            layout.addRow("Reference Trace:", self.ref_trace_combo)
    
    def get_config(self) -> Dict[str, Any]:
        """Get the configuration for creating an analysis."""
        config = self.config.copy()
        
        # Get the trace ID
        trace_idx = self.trace_combo.currentIndex()
        if trace_idx >= 0 and trace_idx < len(self.traces):
            _, trace = self.traces[trace_idx]
            config['input_trace_id'] = trace.id
        else:
            return None  # No valid trace
        
        # Get analysis name
        config['name'] = self.name_edit.text()
        
        # Get analysis-specific config
        if self.analysis_class is PhaseDifference:
            ref_idx = self.ref_trace_combo.currentIndex()
            if ref_idx >= 0 and ref_idx < len(self.traces):
                _, ref_trace = self.traces[ref_idx]
                config['reference_trace_id'] = ref_trace.id
        
        return config

class PlotTab(BaseTab):
    """
    Enhanced plot tab with ROI synchronization, analysis support,
    and efficient toolbar actions.
    """
    
    # Menu signals
    analysis_requested = Signal(Type[Analysis], dict)
    
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
        'roi': 'roi.png',
        'analysis': 'analytics.png'
    }
    
    # Analysis class mapping for menu
    ANALYSIS_CLASSES = {
        'Rise Time': RiseTime,
        'Fall Time': FallTime,
        'Pulse Width': PulseWidth,
        'Phase Difference': PhaseDifference,
        'Slew Rate': SlewRate,
        'Duty Cycle': DutyCycle,
        'Overshoot': Overshoot,
        'Jitter': Jitter,
        'Eye Diagram': EyeDiagram,
        'FFT': FFT,
        'Period': PeriodMeasurement,
        'Peak-to-Peak': PeakToPeak
    }

    def __init__(self, state, model_id: str, parent=None):
        logger.debug(f"Initializing PlotTab for model_id: {model_id}")
        self.plot_view: Optional[PlotView] = None
        # Cache for toolbar buttons/actions
        self._toolbar_buttons = {}
        # List of active analyses
        self._active_analyses = []

        super().__init__(state, model_id, parent)
        
        # Connect to state signals for ROI sync and updates
        self.state.model_changed.connect(self._handle_model_changed)
        
        # Connect to our own signals
        self.analysis_requested.connect(self._create_analysis)
        
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
        
        grid_button = self.toolbar.addToggleButton(
            "Toggle Grid", 
            self._get_icon('grid'),
            checked=True, 
            callback=self._handle_grid_visibility
        )
        self._toolbar_buttons['grid'] = grid_button
        
        roi_button = self.toolbar.addToggleButton(
            "Toggle ROI", 
            self._get_icon('roi'),
            checked=False, 
            callback=self._handle_roi_visibility
        )
        self._toolbar_buttons['roi'] = roi_button
        
        self.toolbar.addSeparator()
        
        self.toolbar.addButton("Group All Traces", self._get_icon('group'), self._handle_group_all_traces)
        self.toolbar.addButton("Isolate All Traces", self._get_icon('isolate'), self._handle_isolate_all_traces)
        
        self.toolbar.addSeparator()
        
        self.toolbar.addButton("Add Marker", self._get_icon('marker'), self._on_add_marker_clicked)
        
        # Add cursor dropdown
        cursor_button = self.toolbar.addButton("Add Cursor", self._get_icon('cursor'))
        cursor_menu = QMenu()
        
        x_cursor_action = QAction("X Cursor", cursor_menu)
        x_cursor_action.triggered.connect(self._on_add_x_cursor_clicked)
        cursor_menu.addAction(x_cursor_action)
        
        y_cursor_action = QAction("Y Cursor", cursor_menu)
        y_cursor_action.triggered.connect(self._on_add_y_cursor_clicked)
        cursor_menu.addAction(y_cursor_action)
        
        cursor_button.setMenu(cursor_menu)
        
        # Add analysis button with submenu
        analysis_button = self.toolbar.addButton("Analysis", self._get_icon('analysis'))
        analysis_menu = QMenu()
        
        # Add analysis submenus by category
        timing_menu = analysis_menu.addMenu("Timing")
        for name in ['Rise Time', 'Fall Time', 'Pulse Width', 'Period', 'Duty Cycle', 'Jitter']:
            action = QAction(name, timing_menu)
            action.triggered.connect(lambda checked, n=name: self._on_analysis_selected(n))
            timing_menu.addAction(action)
        
        amplitude_menu = analysis_menu.addMenu("Amplitude")
        for name in ['Peak-to-Peak', 'Overshoot', 'Slew Rate']:
            action = QAction(name, amplitude_menu)
            action.triggered.connect(lambda checked, n=name: self._on_analysis_selected(n))
            amplitude_menu.addAction(action)
            
        special_menu = analysis_menu.addMenu("Special")
        for name in ['Phase Difference', 'Eye Diagram', 'FFT']:
            action = QAction(name, special_menu)
            action.triggered.connect(lambda checked, n=name: self._on_analysis_selected(n))
            special_menu.addAction(action)
        
        analysis_button.setMenu(analysis_menu)
        
        self.toolbar.addStretch()

    def _on_analysis_selected(self, analysis_name: str):
        """Handle selection of an analysis type from the menu."""
        try:
            logger.debug(f"Selected analysis: {analysis_name}")
            # Get the analysis class
            analysis_class = self.ANALYSIS_CLASSES.get(analysis_name)
            if not analysis_class:
                logger.error(f"Analysis class not found for {analysis_name}")
                return
            
            # Get available traces
            traces = []
            if hasattr(self.plot_view, 'trace_handler'):
                for model, curve in self.plot_view.trace_handler.traces.values():
                    if curve.isVisible():
                        traces.append((model.get_property('name', 'Unnamed'), model))
            
            if not traces:
                logger.warning("No visible traces available for analysis")
                return
                
            # Show configuration dialog
            dialog = AnalysisDialog(analysis_class, traces, self)
            if dialog.exec():
                # Get configuration
                config = dialog.get_config()
                if config:
                    # Request analysis creation
                    self.analysis_requested.emit(analysis_class, config)
                    
        except Exception as e:
            logger.error(f"Error selecting analysis: {e}")

    def _create_analysis(self, analysis_class: Type[Analysis], config: Dict[str, Any]):
        """Create an analysis with the given configuration."""
        try:
            # Create the analysis object
            analysis = analysis_class(**config)
            
            # Register with state
            self.state.register_model(analysis)
            
            # Link to parent plot
            self.state.link_models(self._model_id, analysis.id)
            
            # Add to active analyses
            self._active_analyses.append(analysis.id)
            
            logger.info(f"Created {analysis_class.__name__} analysis: {analysis.id}")
            
        except Exception as e:
            logger.error(f"Error creating analysis: {e}")

    def _handle_model_changed(self, model_id: str, model_type: str, prop: str, value: Any):
        """Handle model changes affecting ROI and grid toggle from the tab perspective."""
        try:
            if not self.model or model_id != self.model.id:
                return
            if prop == 'roi' and self.plot_view:
                self.plot_view.roi.setRegion(value)
            elif prop == 'roi_visible' and self.plot_view:
                self.plot_view.roi_plot_area.setVisible(value)
                if 'roi' in self._toolbar_buttons:
                    # Use QToolButton API for toolbar button
                    self._toolbar_buttons['roi'].setChecked(value)
            elif prop == 'grid_enabled' and 'grid' in self._toolbar_buttons:
                # Use QToolButton API for toolbar button
                self._toolbar_buttons['grid'].setChecked(value)
                
        except Exception as e:
            logger.error(f"Error handling model change: {e}")

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
            logger.debug("Setting all traces to Group mode")
            self.model.begin_update()
            for trace in self.model.get_traces():
                trace.set_property('mode', 'Group')
            self.model.end_update()
            
        except Exception as e:
            logger.error(f"Error grouping all traces: {e}")

    def _handle_isolate_all_traces(self):
        """Set all traces to isolate mode."""
        try:
            if not self.model:
                return
            logger.debug("Setting all traces to Isolate mode")
            self.model.begin_update()
            for trace in self.model.get_traces():
                trace.set_property('mode', 'Isolate')
            self.model.end_update()
            
        except Exception as e:
            logger.error(f"Error isolating all traces: {e}")

    def _handle_roi_visibility(self, visible: bool):
        """Handle ROI visibility toggle."""
        logger.debug(f"ROI visibility toggle triggered: {visible}")
        try:
            if self.plot_view:
                self.plot_view.roi_plot_area.setVisible(visible)
                self.plot_view._apply_roi_update()
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
                
                # Also auto-range isolated view boxes if any
                if hasattr(self.plot_view, 'trace_handler'):
                    for view_box in self.plot_view.trace_handler.isolated_view_boxes.values():
                        if view_box.scene():
                            view_box.enableAutoRange()
                            view_box.autoRange()
                
                # Update ROI to match
                if self.plot_view.roi:
                    x_range = self.plot_view.main_plot_item.getViewBox().viewRange()[0]
                    self.plot_view.roi.setRegion(x_range)
                self.plot_view._suppress_roi_updates = False
                self.plot_view._apply_roi_update()
                
                logger.debug("Auto-range applied to all plots")
                
        except Exception as e:
            logger.error(f"Error in _handle_auto_range: {e}")

    def _on_add_marker_clicked(self):
        """Handle Add Marker button click with efficient trace lookup."""
        try:
            if not self.plot_view or not self.model:
                return

            # Get visible traces for marker placement
            visible_traces = []
            if hasattr(self.plot_view, 'trace_handler'):
                for model, curve in self.plot_view.trace_handler.traces.values():
                    if curve.isVisible():
                        visible_traces.append((model.get_property('name', 'Unnamed'), curve, model))
            
            if not visible_traces:
                logger.warning("No visible traces available for marker placement")
                return

            dialog = MarkerDialog(visible_traces, self)
            if dialog.exec():
                values = dialog.get_values()
                
                logger.debug(f"Marker dialog returned values: {values}")
                
                if values["mode"] == "floating":
                    # Create floating marker as child of plot
                    logger.debug(f"Creating floating marker at ({values['x']}, {values['y']})")
                    
                    # Use the model's create_marker method directly - like your engine does
                    marker = self.model.create_marker(
                        x=values["x"],
                        y=values["y"],
                        name=values["label"],
                        color=values["color"],
                        size=8,
                        symbol="o"
                    )
                    logger.debug(f"Created floating marker {marker.id} at ({values['x']}, {values['y']})")
                    
                    # Explicitly check if it was added to the UI
                    if hasattr(self.plot_view, 'marker_handler'):
                        if marker.id in self.plot_view.marker_handler.markers:
                            logger.debug(f"Marker {marker.id} is in marker_handler.markers")
                        else:
                            logger.warning(f"Marker {marker.id} is NOT in marker_handler.markers")
                    
                else:  # bound mode
                    # Create marker as child of trace using trace's create_marker method
                    trace_model = values["trace_model"]
                    logger.debug(f"Creating trace-bound marker at x={values['x']} for trace {trace_model.id}")
                    
                    marker = trace_model.create_marker(
                        x=values["x"],
                        name=values["label"],
                        color=values["color"],
                        size=8,
                        symbol="o"
                    )
                    logger.debug(f"Created trace-bound marker {marker.id} at x={values['x']}")
                    
                    # Explicitly check if it was added to the UI
                    if hasattr(self.plot_view, 'marker_handler'):
                        if marker.id in self.plot_view.marker_handler.markers:
                            logger.debug(f"Marker {marker.id} is in marker_handler.markers")
                        else:
                            logger.warning(f"Marker {marker.id} is NOT in marker_handler.markers")
                
        except Exception as e:
            logger.error(f"Error in _on_add_marker_clicked: {e}", exc_info=True)

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
            
            logger.debug(f"Added X cursor at position {pos}")
            
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
            
            logger.debug(f"Added Y cursor at position {pos}")
            
        except Exception as e:
            logger.error(f"Error in _on_add_y_cursor_clicked: {e}")

    def _get_icon(self, name: str) -> QIcon:
        """Get cached icon from the icons directory."""
        icon_file = self.TOOLBAR_ICONS.get(name)
        if icon_file:
            icon_path = str(Path(__file__).parent.parent / 'icons' / icon_file)
            return QIcon(icon_path)
        return QIcon()
    
    def set_status(self, message):
        """Set status message via the application state."""
        if hasattr(self, 'state') and self.state:
            self.state.set_status(message)
        else:
            logger.debug(f"Status: {message}")  # Fallback if state is not available


class MarkerDialog(QDialog):
    """
    Enhanced dialog for marker creation with intuitive trace binding.
    """
    def __init__(self, traces, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Marker")
        self.setModal(True)
        self.traces = traces  # [(name, curve, model)]

        layout = QFormLayout(self)
        layout.setSpacing(10)

        # Marker mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Floating Marker (free position)", "floating")
        self.mode_combo.addItem("Bound to Trace (follows trace data)", "bound")
        self.mode_combo.currentIndexChanged.connect(self._update_ui_for_mode)
        layout.addRow("Marker Type:", self.mode_combo)

        # Trace selection (only visible for bound markers)
        self.trace_combo = QComboBox()
        for name, curve, _ in traces:
            self.trace_combo.addItem(name, (curve, _))
        self.trace_label = QLabel("Trace:")
        layout.addRow(self.trace_label, self.trace_combo)

        # X position input
        self.x_pos = QDoubleSpinBox()
        self.x_pos.setRange(-1e9, 1e9)
        self.x_pos.setDecimals(6)
        self.x_pos.setStepType(QDoubleSpinBox.AdaptiveDecimalStepType)
        self.x_pos.setButtonSymbols(QDoubleSpinBox.NoButtons)
        layout.addRow("X Position:", self.x_pos)

        # Y position input (only visible for floating markers)
        self.y_pos = QDoubleSpinBox()
        self.y_pos.setRange(-1e9, 1e9)
        self.y_pos.setDecimals(6)
        self.y_pos.setStepType(QDoubleSpinBox.AdaptiveDecimalStepType)
        self.y_pos.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self.y_label = QLabel("Y Position:")
        layout.addRow(self.y_label, self.y_pos)

        # Marker label
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Enter marker label...")
        layout.addRow("Label:", self.label_input)
        
        # Color selection
        self.color_combo = QComboBox()
        colors = [
            ("Yellow", "#FFFF00"), 
            ("Red", "#FF0000"),
            ("Green", "#00FF00"),
            ("Blue", "#0000FF"),
            ("Cyan", "#00FFFF"),
            ("Magenta", "#FF00FF"),
            ("White", "#FFFFFF")
        ]
        for name, color in colors:
            self.color_combo.addItem(name, color)
        layout.addRow("Color:", self.color_combo)

        # Add a "place on graph" button with instructions
        self.place_button = QPushButton("Place on Graph")
        self.place_button.setToolTip("Click on the graph to place the marker at that position")
        self.place_button.clicked.connect(self._on_place_clicked)
        layout.addRow("", self.place_button)
        
        # Button row
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
        
        # Initialize UI based on current mode
        self._update_ui_for_mode()
        
        # Store parent for access to plot view
        self.parent_tab = parent

    def _update_ui_for_mode(self):
        """Update UI elements based on selected marker mode."""
        mode = self.mode_combo.currentData()
        
        # Show/hide Y position field based on mode
        self.y_pos.setVisible(mode == "floating")
        self.y_label.setVisible(mode == "floating")
        
        # Trace selection is only relevant for bound markers
        self.trace_combo.setVisible(mode == "bound")
        self.trace_label.setVisible(mode == "bound")
        
        # Update layout
        self.adjustSize()

    def _on_place_clicked(self):
        """Handle place button click - enter placement mode."""
        # Hide the dialog while placing
        self.hide()
        
        # Get the plot view from parent tab
        if hasattr(self.parent_tab, 'plot_view') and self.parent_tab.plot_view:
            plot_view = self.parent_tab.plot_view
            
            # Show instructions
            self.parent_tab.set_status("Click on the plot to place marker")
            
            # Connect to click event (one shot)
            plot_view.main_plot_item.scene().sigMouseClicked.connect(self._handle_plot_click)
        else:
            # If can't get plot view, just show dialog again
            self.show()

    def _handle_plot_click(self, event):
        """Handle click on plot to get marker position."""
        try:
            # Disconnect to ensure one-shot behavior
            plot_view = self.parent_tab.plot_view
            plot_view.main_plot_item.scene().sigMouseClicked.disconnect(self._handle_plot_click)
            
            # Get click position in plot coordinates
            pos = plot_view.main_plot_item.vb.mapSceneToView(event.scenePos())
            
            # Set position values in dialog
            self.x_pos.setValue(pos.x())
            
            # If in floating mode, also set y value
            if self.mode_combo.currentData() == "floating":
                self.y_pos.setValue(pos.y())
            # If in bound mode, find closest point on selected trace
            else:
                self._update_bound_y_preview()
                
            # Clear status and show dialog again
            if hasattr(self.parent_tab, 'set_status'):
                self.parent_tab.set_status("")
            self.show()
        except Exception as e:
            logger.error(f"Error handling plot click: {e}")
            # Make sure the dialog is shown even if there's an error
            self.show()

    def _update_bound_y_preview(self):
        """Update y value preview for bound markers."""
        try:
            # Get currently selected trace
            _, trace_model = self.trace_combo.currentData()
            x_val = self.x_pos.value()
            
            # Get trace data and interpolate y
            x_data, y_data = trace_model.data
            if len(x_data) > 0:
                if len(x_data) > 1:
                    # Find closest or interpolated value
                    idx = np.searchsorted(x_data, x_val)
                    if idx == 0:
                        y = y_data[0]
                    elif idx >= len(x_data):
                        y = y_data[-1]
                    else:
                        # Interpolate between points
                        x0, x1 = x_data[idx-1], x_data[idx]
                        y0, y1 = y_data[idx-1], y_data[idx]
                        if x1 == x0:
                            y = y0
                        else:
                            ratio = (x_val - x0) / (x1 - x0)
                            y = y0 + ratio * (y1 - y0)
                else:
                    y = y_data[0]
                
                # Update label to show expected y value
                self.trace_label.setText(f"Trace: (y ≈ {y:.6g})")
        except Exception as e:
            logger.error(f"Error updating bound y preview: {e}")

    def get_values(self):
        """Get dialog values with proper defaults."""
        mode = self.mode_combo.currentData()
        x_pos = self.x_pos.value()
        
        if mode == "floating":
            # Floating marker - needs both x and y
            y_pos = self.y_pos.value()
            label = self.label_input.text() or f"Marker ({x_pos:.2f}, {y_pos:.2f})"
            color = self.color_combo.currentData()
            return {
                "mode": "floating",
                "x": x_pos,
                "y": y_pos,
                "label": label,
                "color": color
            }
        else:
            # Bound marker - just needs trace and x
            curve, trace_model = self.trace_combo.currentData()
            label = self.label_input.text() or f"Marker ({x_pos:.2f})"
            color = self.color_combo.currentData()
            return {
                "mode": "bound",
                "trace_model": trace_model,
                "x": x_pos,
                "label": label,
                "color": color
            }