# pymetr/views/tabs/plot_tab.py
from pathlib import Path
from typing import Optional, Any
from PySide6.QtWidgets import (
    QVBoxLayout, QSplitter, QWidget,
    QLabel, QSizePolicy, QDialog, QFormLayout,
    QComboBox, QDoubleSpinBox, QPushButton, QHBoxLayout, QLineEdit
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QAction, QIcon
import pyqtgraph as pg
import numpy as np

from pymetr.views.tabs.base import BaseTab
from pymetr.views.widgets.plot_view import PlotView
from pymetr.core.logging import logger


class PlotTab(BaseTab):
    """Full-featured plot tab with ROI, markers, cursors and toolbar."""
    
    # Icon mapping for toolbar actions
    TOOLBAR_ICONS = {
        'zoom': 'zoom_in.png',
        'group': 'group.png',
        'isolate': 'isolate.png',
        'marker': 'markers.png',
        'cursor': 'cursor.png',
        'camera': 'camera.png',
        'save': 'save.png',
        'visibility': 'visibility_on.png',
        'traces': 'traces.png',
        'analytics': 'analytics.png'
    }
    
    def _get_icon(self, name: str) -> QIcon:
        """Get icon from the icons directory."""
        icon_file = self.TOOLBAR_ICONS.get(name)
        if icon_file:
            icon_path = str(Path(__file__).parent.parent / 'icons' / icon_file)
            return QIcon(icon_path)
        return QIcon()
    
    def __init__(self, state, model_id: str, parent=None):
        logger.debug(f"Initializing PlotTab for model_id: {model_id}")
        # Initialize member variables
        self.plot_view: Optional[PlotView] = None
        self.roi_plot_area: Optional[pg.PlotWidget] = None
        self.roi_plot_item: Optional[pg.PlotItem] = None
        self.roi: Optional[pg.LinearRegionItem] = None

        # ROI update handling
        self._roi_update_needed = False
        self._suppress_roi_updates = False
        self.roi_update_timer = QTimer()
        self.roi_update_timer.setSingleShot(True)
        self.roi_update_timer.timeout.connect(self._apply_roi_update)

        # Call base class init
        super().__init__(state, model_id, parent)
        logger.debug(f"PlotTab initialized for model {model_id}")

    def _setup_ui(self):
        """Initialize the tab UI components."""
        logger.debug("Setting up UI for PlotTab")
        try:
            # Create a layout for the content widget
            layout = QVBoxLayout(self.content_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            logger.debug("Content widget layout created for PlotTab")

            # Create main plot view
            logger.debug("Creating main PlotView")
            self.plot_view = PlotView(self.state, self._model_id, self)
            layout.addWidget(self.plot_view)
            logger.debug("Main PlotView added to layout")

            # Create a container for the ROI plot area
            logger.debug("Creating ROI container widget")
            roi_container = QWidget()
            roi_layout = QVBoxLayout(roi_container)
            roi_layout.setContentsMargins(0, 0, 0, 0)
            roi_layout.setSpacing(0)

            # Setup ROI plot area and add it to the container
            logger.debug("Setting up ROI plot area")
            self._setup_roi_plot()
            roi_layout.addWidget(self.roi_plot_area)
            logger.debug("ROI plot area added to ROI container")

            # Add the ROI container to the main layout
            layout.addWidget(roi_container)
            logger.debug("ROI container added to main layout")

            # Setup toolbar actions
            logger.debug("Setting up toolbar for PlotTab")
            self._setup_toolbar()

            # Connect plot signals
            if hasattr(self.plot_view, 'plot_item'):
                logger.debug("Connecting plot range-changed signal")
                self.plot_view.plot_item.sigRangeChanged.connect(
                    self._handle_main_plot_range_changed
                )
            else:
                logger.warning("PlotView has no attribute 'plot_item'")
        except Exception as e:
            logger.error(f"Error during PlotTab UI setup: {e}")

    def _setup_toolbar(self):
        """Setup toolbar actions."""
        logger.debug("Setting up toolbar actions for PlotTab")
        try:
            # --- View Menu ---
            view_menu = self.toolbar.addDropdown("View")
            logger.debug("Added 'View' dropdown to toolbar")

            # ROI visibility toggle
            self.show_roi_action = QAction("Show ROI", view_menu)
            self.show_roi_action.setCheckable(True)
            self.show_roi_action.setChecked(True)
            self.show_roi_action.triggered.connect(self._handle_roi_visibility)
            view_menu.addAction(self.show_roi_action)
            logger.debug("ROI visibility toggle added to toolbar")

            view_menu.addSeparator()

            # Auto range action
            auto_range_action = QAction("Auto Range", view_menu)
            auto_range_action.triggered.connect(self._handle_auto_range)
            view_menu.addAction(auto_range_action)
            logger.debug("Auto Range action added to toolbar")

            # --- New Actions for Markers and Cursors ---
            self.toolbar.addSeparator()
            self.toolbar.addButton(
                "Add Marker",
                self._get_icon('marker'),
                self._on_add_marker_clicked
            )
            logger.debug("Add Marker action added to toolbar")

            self.toolbar.addButton(
                "Add X Cursor",
                self._get_icon('cursor'),
                self._on_add_x_cursor_clicked
            )
            logger.debug("Add X Cursor action added to toolbar")

            self.toolbar.addButton(
                "Add Y Cursor",
                self._get_icon('cursor'),
                self._on_add_y_cursor_clicked
            )
            logger.debug("Add Y Cursor action added to toolbar")

            self.toolbar.addSeparator()
            self.toolbar.addStretch()
            logger.debug("Toolbar setup for PlotTab complete")
        except Exception as e:
            logger.error(f"Error setting up toolbar in PlotTab: {e}")

    def _setup_roi_plot(self):
        """Setup the ROI plot area."""
        logger.debug("Setting up ROI plot area in PlotTab")
        try:
            self.roi_plot_area = pg.PlotWidget()
            self.roi_plot_area.setMinimumHeight(60)
            self.roi_plot_area.setMaximumHeight(60)
            self.roi_plot_area.setSizePolicy(
                QSizePolicy.Expanding, 
                QSizePolicy.Fixed
            )
            self.roi_plot_area.setBackground('#2A2A2A')
            logger.debug("ROI plot area widget created")

            self.roi_plot_item = self.roi_plot_area.getPlotItem()
            self.roi_plot_item.showGrid(x=True, y=False)
            self.roi_plot_item.getAxis('left').hide()
            self.roi_plot_item.setMouseEnabled(x=False, y=False)
            logger.debug("ROI plot item configured (grid, axis, mouse settings)")

            # Style the bottom axis
            bottom_axis = self.roi_plot_item.getAxis('bottom')
            bottom_axis.setPen(pg.mkPen('w'))
            bottom_axis.setTextPen(pg.mkPen('w'))
            logger.debug("Bottom axis styling applied in ROI plot")

            # Add ROI selector
            self.roi = pg.LinearRegionItem()
            self.roi_plot_item.addItem(self.roi)
            self.roi.sigRegionChanged.connect(self._handle_roi_changed)
            logger.debug("ROI selector added and connected")
        except Exception as e:
            logger.error(f"Error in _setup_roi_plot: {e}")

    def _handle_roi_visibility(self, visible: bool):
        """Handle ROI visibility toggle."""
        logger.debug(f"ROI visibility toggle triggered: {visible}")
        try:
            self.roi_plot_area.setVisible(visible)
            if self.model:
                self.model.set_property('roi_visible', visible)
                logger.debug(f"Model property 'roi_visible' set to {visible}")
        except Exception as e:
            logger.error(f"Error in _handle_roi_visibility: {e}")

    def _handle_auto_range(self):
        """Handle auto range action."""
        logger.debug("Auto range action triggered")
        try:
            if self.plot_view:
                self._suppress_roi_updates = True
                self.plot_view.autoRange()
                self._suppress_roi_updates = False
                logger.debug("Auto range applied successfully")
            else:
                logger.error("PlotView not available in _handle_auto_range")
        except Exception as e:
            logger.error(f"Error in _handle_auto_range: {e}")

    def _handle_roi_changed(self):
        """Handle ROI region changes."""
        try:
            if not self.model or self._suppress_roi_updates:
                logger.debug("Either no model or ROI updates suppressed; returning")
                return
            region = self.roi.getRegion()
            region_list = [float(x) for x in region]
            if region_list != self.model.get_property('roi'):
                logger.debug("New ROI region differs from model property; updating model")
                self.model.set_property('roi', region_list)
                self._suppress_roi_updates = True
                if hasattr(self.plot_view, 'plot_item'):
                    self.plot_view.plot_item.setXRange(*region, padding=0)
                    logger.debug("PlotView X range updated to ROI region")
                else:
                    logger.warning("PlotView has no attribute 'plot_item'")
                self._suppress_roi_updates = False
        except Exception as e:
            logger.error(f"Error in _handle_roi_changed: {e}")

    @Slot(object, object)
    def _handle_main_plot_range_changed(self, viewbox, ranges):
        """Update ROI when main plot range changes."""
        logger.debug(f"Main plot range changed: {ranges}")
        try:
            if self._suppress_roi_updates:
                logger.debug("ROI updates are suppressed; skipping _handle_main_plot_range_changed")
                return
            if self.roi:
                self.roi.setRegion(ranges[0])
                logger.debug(f"ROI region set to: {ranges[0]}")
            # Queue ROI plot update
            self._roi_update_needed = True
            self.roi_update_timer.start(100)
            logger.debug("ROI update timer started")
        except Exception as e:
            logger.error(f"Error in _handle_main_plot_range_changed: {e}")

    def _apply_roi_update(self):
        """Apply queued ROI updates."""
        logger.debug("Applying ROI update")
        try:
            if not self._roi_update_needed or not self.plot_view:
                logger.debug("No ROI update needed or PlotView unavailable")
                return

            self.roi_plot_area.clear()
            logger.debug("Cleared ROI plot area")

            if not self.model:
                logger.error("No model found in _apply_roi_update; aborting update")
                return

            # Calculate full data range efficiently
            x_ranges = []
            for trace_id, curve in self.plot_view.traces.items():
                if curve.isVisible():
                    data = curve.getData()
                    if data[0].size > 0:
                        rmin = np.nanmin(data[0])
                        rmax = np.nanmax(data[0])
                        x_ranges.append((rmin, rmax))
                        logger.debug(f"Trace {trace_id}: x-range = ({rmin}, {rmax})")

            if x_ranges:
                x_min = min(r[0] for r in x_ranges)
                x_max = max(r[1] for r in x_ranges)
                if np.isfinite(x_min) and np.isfinite(x_max):
                    padding = (x_max - x_min) * 0.05
                    self.roi_plot_item.setXRange(x_min - padding, x_max + padding, padding=0)
                    logger.debug(f"ROI plot X range set to ({x_min - padding}, {x_max + padding})")

            # Add visible traces to ROI plot efficiently
            for trace_id, curve in self.plot_view.traces.items():
                if curve.isVisible():
                    data = curve.getData()
                    self.roi_plot_area.plot(data[0], data[1], pen=curve.opts['pen'])
                    logger.debug(f"Plotted trace {trace_id} on ROI plot")

            # Re-add ROI
            self.roi_plot_area.addItem(self.roi)
            self._roi_update_needed = False
            logger.debug("ROI update applied successfully")
        except Exception as e:
            logger.error(f"Error in _apply_roi_update: {e}")

    def set_model(self, model_id: str):
        """Set up model and manage ROI state."""
        logger.debug(f"PlotTab set_model called for model_id: {model_id}")
        try:
            super().set_model(model_id)
            if self.model:
                # Set initial ROI state
                roi = self.model.get_property("roi", None)
                if roi and len(roi) == 2 and self.roi:
                    self.roi.setRegion(roi)
                    logger.debug(f"Initial ROI state set to {roi}")
                else:
                    logger.debug("No initial ROI state available")

                # Set ROI visibility
                roi_visible = self.model.get_property("roi_visible", True)
                self.roi_plot_area.setVisible(roi_visible)
                self.show_roi_action.setChecked(roi_visible)
                logger.debug(f"ROI visibility set to {roi_visible}")

                # Initial ROI plot update
                self._roi_update_needed = True
                self.roi_update_timer.start(100)
                logger.debug("ROI update timer started for initial update")
            else:
                logger.error("No model found in set_model for PlotTab")
        except Exception as e:
            logger.error(f"Error in set_model of PlotTab: {e}")

    # --- New UI Event Handlers for Markers and Cursors ---

    def _on_add_marker_clicked(self):
        """UI event: handle Add Marker button clicked."""
        logger.debug("Add Marker button clicked")
        try:
            # Open the MarkerDialog with a list of current traces.
            trace_list = list(self.plot_view.traces.values())
            dialog = MarkerDialog(trace_list, self)
            if dialog.exec():
                trace, x_pos, label = dialog.get_values()
                # Compute the y value from the selected trace data
                data = trace.getData()
                if data[0].size > 0:
                    idx = np.abs(data[0] - x_pos).argmin()
                    y_val = data[1][idx]
                    logger.debug(f"Marker details: trace={trace.opts.get('name','')}, x={x_pos}, y={y_val}, label={label}")
                    if self.model:
                        self.model.create_marker(
                            x=x_pos,
                            y=y_val,
                            label=label,
                            color="yellow",
                            size=8,
                            symbol="o"
                        )
                else:
                    logger.warning("Selected trace has no data.")
        except Exception as e:
            logger.error(f"Error in _on_add_marker_clicked: {e}")

    def _on_add_x_cursor_clicked(self):
        """UI event: handle Add X Cursor button clicked."""
        logger.debug("Add X Cursor button clicked")
        try:
            if self.plot_view and hasattr(self.plot_view, 'plot_item'):
                # Use the center of the current x-range
                x_range = self.plot_view.plot_item.getViewBox().viewRange()[0]
                pos = (x_range[0] + x_range[1]) / 2.0
                logger.debug(f"Adding X cursor at position {pos}")
                if self.model:
                    self.model.create_cursor(
                        axis="x",
                        position=pos,
                        color="yellow",
                        style="dash",
                        width=1,
                        visible=True
                    )
            else:
                logger.error("PlotView or plot_item unavailable for adding X cursor.")
        except Exception as e:
            logger.error(f"Error in _on_add_x_cursor_clicked: {e}")

    def _on_add_y_cursor_clicked(self):
        """UI event: handle Add Y Cursor button clicked."""
        logger.debug("Add Y Cursor button clicked")
        try:
            if self.plot_view and hasattr(self.plot_view, 'plot_item'):
                # Use the center of the current y-range
                y_range = self.plot_view.plot_item.getViewBox().viewRange()[1]
                pos = (y_range[0] + y_range[1]) / 2.0
                logger.debug(f"Adding Y cursor at position {pos}")
                if self.model:
                    self.model.create_cursor(
                        axis="y",
                        position=pos,
                        color="magenta",
                        style="dot",
                        width=1,
                        visible=True
                    )
            else:
                logger.error("PlotView or plot_item unavailable for adding Y cursor.")
        except Exception as e:
            logger.error(f"Error in _on_add_y_cursor_clicked: {e}")


# --- Minimal MarkerDialog Implementation ---
class MarkerDialog(QDialog):
    """
    Simple dialog for creating a marker.
    Allows the user to choose a trace, enter an x value, and provide a marker label.
    """
    def __init__(self, traces, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Marker")
        self.setModal(True)

        layout = QFormLayout(self)

        # Trace selector: create a dropdown that lists trace names.
        self.trace_combo = QComboBox()
        for trace in traces:
            name = trace.opts.get('name', 'Unnamed Trace')
            self.trace_combo.addItem(name, trace)
        layout.addRow("Trace:", self.trace_combo)

        # X position input
        self.x_pos = QDoubleSpinBox()
        self.x_pos.setRange(-1e6, 1e6)
        self.x_pos.setDecimals(6)
        layout.addRow("X Position:", self.x_pos)

        # Marker label input using QLineEdit
        self.label_input = QLineEdit()
        layout.addRow("Marker Label:", self.label_input)

        # Buttons
        btn_box = QWidget()
        btn_layout = QHBoxLayout(btn_box)
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_box)

    def get_values(self):
        """Return the selected trace, x position, and marker label."""
        trace = self.trace_combo.currentData()
        x_pos = self.x_pos.value()
        label = self.label_input.text() or "Marker"
        return trace, x_pos, label



# from pathlib import Path
# from typing import Optional
# from PySide6.QtWidgets import (
#     QVBoxLayout, QWidget, QSizePolicy, 
#     QMenu, QDialog, QFormLayout, QComboBox,
#     QDoubleSpinBox, QPushButton, QHBoxLayout
# )
# from PySide6.QtCore import Qt, Slot, QTimer
# from PySide6.QtGui import QAction, QIcon, QCursor
# import pyqtgraph as pg
# import numpy as np

# from pymetr.views.tabs.base import BaseTab
# from pymetr.views.widgets.plot_view import PlotView
# from pymetr.core.logging import logger

# class MarkerDialog(QDialog):
#     """Dialog for creating a marker with trace selection."""
#     def __init__(self, traces, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Add Marker")
        
#         layout = QFormLayout(self)
        
#         # Trace selector
#         self.trace_combo = QComboBox()
#         for trace in traces:
#             self.trace_combo.addItem(trace.name, trace)
#         layout.addRow("Trace:", self.trace_combo)
        
#         # X position input
#         self.x_pos = QDoubleSpinBox()
#         self.x_pos.setRange(-1e6, 1e6)
#         self.x_pos.setDecimals(6)
#         layout.addRow("X Position:", self.x_pos)
        
#         # Buttons
#         btn_box = QWidget()
#         btn_layout = QHBoxLayout(btn_box)
        
#         ok_btn = QPushButton("OK")
#         ok_btn.clicked.connect(self.accept)
#         cancel_btn = QPushButton("Cancel")
#         cancel_btn.clicked.connect(self.reject)
        
#         btn_layout.addWidget(ok_btn)
#         btn_layout.addWidget(cancel_btn)
#         layout.addRow(btn_box)

#     def get_values(self):
#         """Return selected trace and x position."""
#         trace = self.trace_combo.currentData()
#         x_pos = self.x_pos.value()
#         return trace, x_pos

# class CursorDialog(QDialog):
#     """Dialog for creating a cursor."""
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setWindowTitle("Add Cursor")
        
#         layout = QFormLayout(self)
        
#         # Axis selector
#         self.axis_combo = QComboBox()
#         self.axis_combo.addItem("Vertical (X)", "x")
#         self.axis_combo.addItem("Horizontal (Y)", "y")
#         layout.addRow("Type:", self.axis_combo)
        
#         # Position input
#         self.position = QDoubleSpinBox()
#         self.position.setRange(-1e6, 1e6)
#         self.position.setDecimals(6)
#         layout.addRow("Position:", self.position)
        
#         # Buttons
#         btn_box = QWidget()
#         btn_layout = QHBoxLayout(btn_box)
        
#         ok_btn = QPushButton("OK")
#         ok_btn.clicked.connect(self.accept)
#         cancel_btn = QPushButton("Cancel")
#         cancel_btn.clicked.connect(self.reject)
        
#         btn_layout.addWidget(ok_btn)
#         btn_layout.addWidget(cancel_btn)
#         layout.addRow(btn_box)

#     def get_values(self):
#         """Return selected axis and position."""
#         axis = self.axis_combo.currentData()
#         pos = self.position.value()
#         return axis, pos
    
# class PlotTab(BaseTab):
#     """
#     Full-featured plot tab with ROI and toolbar.
#     Provides controls for:
#     - View manipulation (zoom, pan, auto-range)
#     - Trace management (group/isolate)
#     - Analysis tools (markers, cursors)
#     - Export options
#     """
    
#     # Icon mapping for toolbar actions
#     TOOLBAR_ICONS = {
#         'zoom': 'zoom_in.png',
#         'group': 'group.png',
#         'isolate': 'isolate.png',
#         'marker': 'markers.png',
#         'cursor': 'cursor.png',
#         'camera': 'camera.png',
#         'save': 'save.png',
#         'visibility': 'visibility_on.png',
#         'traces': 'traces.png',
#         'analytics': 'analytics.png'
#     }

#     def __init__(self, state, model_id: str, parent=None):
#         """Initialize PlotTab with plot and ROI views."""
#         # Initialize member variables before super() call
#         self.plot_view: Optional[PlotView] = None
#         self.roi_plot_area: Optional[pg.PlotWidget] = None
#         self.roi_plot_item: Optional[pg.PlotItem] = None
#         self.roi: Optional[pg.LinearRegionItem] = None
        
#         # ROI update handling
#         self._roi_update_needed = False
#         self._suppress_roi_updates = False
#         self.roi_update_timer = QTimer()
#         self.roi_update_timer.setSingleShot(True)
#         self.roi_update_timer.timeout.connect(self._handle_roi_update)

#         self.show_roi_action = None
        
#         super().__init__(state, model_id, parent)
#         logger.debug(f"PlotTab initialized for model {model_id}")

#     def _get_icon(self, name: str) -> QIcon:
#         """Get icon from the icons directory."""
#         icon_file = self.TOOLBAR_ICONS.get(name)
#         if icon_file:
#             icon_path = str(Path(__file__).parent.parent / 'icons' / icon_file)
#             return QIcon(icon_path)
#         return QIcon()

#     def _setup_ui(self):
#         """Initialize plot and ROI components."""
#         layout = QVBoxLayout(self.content_widget)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(0)
        
#         # Create main plot view
#         self.plot_view = PlotView(self.state, self._model_id, self)
#         layout.addWidget(self.plot_view)
        
#         # Create ROI container and setup
#         roi_container = QWidget()
#         roi_layout = QVBoxLayout(roi_container)
#         roi_layout.setContentsMargins(0, 0, 0, 0)
#         roi_layout.setSpacing(0)
        
#         self._setup_roi_plot()
#         roi_layout.addWidget(self.roi_plot_area)
#         layout.addWidget(roi_container)
        
#         # Connect plot signals
#         if hasattr(self.plot_view, 'plot_item'):
#             self.plot_view.plot_item.sigRangeChanged.connect(
#                 self._handle_plot_range_changed
#             )

#     def _setup_toolbar(self):
#         """Setup toolbar actions and menus."""
#         # --- View Menu ---
#         view_menu = self.toolbar.addDropdown("View")
        
#         # ROI visibility toggle
#         self.show_roi_action = QAction("Show ROI", view_menu)
#         self.show_roi_action.setIcon(self._get_icon('visibility'))
#         self.show_roi_action.setCheckable(True)
#         self.show_roi_action.setChecked(True)
#         self.show_roi_action.triggered.connect(self._on_roi_toggled)
#         view_menu.addAction(self.show_roi_action)
        
#         # Auto range action
#         auto_range_action = QAction("Auto Range", self)
#         auto_range_action.setIcon(self._get_icon('zoom'))
#         auto_range_action.triggered.connect(self._on_auto_range_clicked)
#         self.toolbar.addAction(auto_range_action)
        
#         # --- Trace Menu ---
#         trace_menu = self.toolbar.addDropdown("Traces")
#         trace_menu.setIcon(self._get_icon('traces'))
        
#         # Group/Isolate all actions
#         group_all_action = QAction("Group All Traces", trace_menu)
#         group_all_action.setIcon(self._get_icon('group'))
#         group_all_action.triggered.connect(self._on_group_all_clicked)
#         trace_menu.addAction(group_all_action)
        
#         isolate_all_action = QAction("Isolate All Traces", trace_menu)
#         isolate_all_action.setIcon(self._get_icon('isolate'))
#         isolate_all_action.triggered.connect(self._on_isolate_all_clicked)
#         trace_menu.addAction(isolate_all_action)
        
#         # --- Analysis Tools ---
#         self.toolbar.addSeparator()
        
#         add_marker_action = QAction("Add Marker", self)
#         add_marker_action.setIcon(self._get_icon('marker'))
#         add_marker_action.triggered.connect(self._on_add_marker_clicked)
#         self.toolbar.addAction(add_marker_action)
        
#         add_cursor_action = QAction("Add Cursor", self)
#         add_cursor_action.setIcon(self._get_icon('cursor'))
#         add_cursor_action.triggered.connect(self._on_add_cursor_clicked)
#         self.toolbar.addAction(add_cursor_action)
        
#         # --- Export Menu ---
#         export_menu = self.toolbar.addDropdown("Export")
#         export_menu.setIcon(self._get_icon('save'))
        
#         # Screenshot action
#         screenshot_action = QAction("Copy to Clipboard", export_menu)
#         screenshot_action.setIcon(self._get_icon('camera'))
#         screenshot_action.triggered.connect(self._on_screenshot_clicked)
#         export_menu.addAction(screenshot_action)
        
#         # Export actions
#         for fmt in ["PNG", "JPEG", "SVG"]:
#             action = QAction(f"Save as {fmt}...", export_menu)
#             action.setIcon(self._get_icon('save'))
#             action.triggered.connect(lambda checked, f=fmt: self._on_export_clicked(f))
#             export_menu.addAction(action)
#         self.toolbar.addStretch()

#     def _setup_roi_plot(self):
#         """Setup the ROI plot area."""
#         self.roi_plot_area = pg.PlotWidget()
#         self.roi_plot_area.setMinimumHeight(60)
#         self.roi_plot_area.setMaximumHeight(60)
#         self.roi_plot_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
#         self.roi_plot_area.setBackground('#2A2A2A')
        
#         self.roi_plot_item = self.roi_plot_area.getPlotItem()
#         self.roi_plot_item.showGrid(x=True, y=False)
#         self.roi_plot_item.getAxis('left').hide()
#         self.roi_plot_item.setMouseEnabled(x=False, y=False)
        
#         # Style bottom axis
#         bottom_axis = self.roi_plot_item.getAxis('bottom')
#         bottom_axis.setPen(pg.mkPen('w'))
#         bottom_axis.setTextPen(pg.mkPen('w'))
        
#         # Add ROI selector
#         self.roi = pg.LinearRegionItem()
#         self.roi_plot_item.addItem(self.roi)
#         self.roi.sigRegionChanged.connect(self._handle_roi_changed)

#     def _on_roi_toggled(self, visible: bool):
#         """Handle ROI visibility toggle from toolbar."""
#         self.roi_plot_area.setVisible(visible)
#         if self.model:
#             self.model.roi_visible = visible

#     def _on_auto_range_clicked(self):
#         """Handle auto range button click."""
#         if self.plot_view:
#             self._suppress_roi_updates = True
#             self.plot_view.autoRange()
#             self._suppress_roi_updates = False

#     def _on_group_all_clicked(self):
#         """Handle group all traces button click."""
#         if not self.model:
#             return
#         for trace in self.model.get_traces():
#             trace.mode = "Group"

#     def _on_isolate_all_clicked(self):
#         """Handle isolate all traces button click."""
#         if not self.model:
#             return
#         for trace in self.model.get_traces():
#             trace.mode = "Isolate"

#     def _on_screenshot_clicked(self):
#         """Handle screenshot button click."""
#         if self.plot_view:
#             self.plot_view.copy_to_clipboard()

#     def _on_export_clicked(self, format: str):
#         """Handle export button click."""
#         if not self.plot_view:
#             return
            
#         file_formats = {
#             "PNG": ("PNG files", "*.png"),
#             "JPEG": ("JPEG files", "*.jpg"),
#             "SVG": ("SVG files", "*.svg")
#         }
        
#         fmt = file_formats.get(format)
#         if fmt:
#             self.plot_view.export_plot(*fmt)

#     # Internal state handlers remain with _handle_ prefix:
#     def _handle_roi_changed(self):
#         """Handle ROI region changes from user interaction."""
#         if not self.model or self._suppress_roi_updates:
#             return
            
#         region = self.roi.getRegion()
#         region_list = [float(x) for x in region]
        
#         current_roi = self.model.roi
#         if current_roi != region_list:
#             self._suppress_roi_updates = True
#             self.model.roi = region_list
#             if hasattr(self.plot_view, 'plot_item'):
#                 self.plot_view.plot_item.setXRange(*region, padding=0)
#             self._suppress_roi_updates = False

#     def _handle_roi_update(self):
#         """Update ROI plot area after range changes."""
#         if not self._roi_update_needed or not self.plot_view:
#             return
#         if not self.model or self._suppress_roi_updates:
#             return
            
#         region = self.roi.getRegion()
#         region_list = [float(x) for x in region]
        
#         if region_list != self.model.roi:
#             self._suppress_roi_updates = True
#             self.model.roi = region_list
#             if hasattr(self.plot_view, 'plot_item'):
#                 self.plot_view.plot_item.setXRange(*region, padding=0)
#             self._suppress_roi_updates = False

#     @Slot(object, object)
#     def _handle_plot_range_changed(self, viewbox, ranges):
#         """Handle plot range changes from pyqtgraph."""
#         if self._suppress_roi_updates:
#             return
            
#         if self.roi:
#             self.roi.setRegion(ranges[0])
            
#         self._roi_update_needed = True
#         self.roi_update_timer.start(100)

#     def _on_add_marker_clicked(self):
#         """Handle add marker button click."""
#         if not self.model:
#             return
            
#         traces = self.model.get_traces()
#         if not traces:
#             logger.warning("No traces available for marker placement")
#             return
            
#         dialog = MarkerDialog(traces, self)
#         if dialog.exec_():
#             trace, x_pos = dialog.get_values()
            
#             # Find Y value at X position
#             try:
#                 idx = np.abs(trace.x_data - x_pos).argmin()
#                 y_pos = trace.y_data[idx]
                
#                 # Create marker
#                 marker = self.model.create_marker(
#                     x=x_pos,
#                     y=y_pos,
#                     label=f"Marker {len(self.model.get_markers()) + 1}",
#                     color="yellow",
#                     size=8,
#                     symbol="o"
#                 )
#                 logger.debug(f"Created marker {marker.id} at ({x_pos}, {y_pos})")
#             except Exception as e:
#                 logger.error(f"Error creating marker: {e}")

#     def _on_add_cursor_clicked(self):
#         """Handle add cursor button click."""
#         if not self.model:
#             return
            
#         dialog = CursorDialog(self)
#         if dialog.exec_():
#             axis, position = dialog.get_values()
            
#             try:
#                 cursor = self.model.create_cursor(
#                     axis=axis,
#                     position=position,
#                     color="yellow",
#                     style="dash",
#                     width=1
#                 )
#                 logger.debug(f"Created {axis}-axis cursor {cursor.id} at position {position}")
#             except Exception as e:
#                 logger.error(f"Error creating cursor: {e}")

#     def set_model(self, model_id: str):
#         """Set up model and manage ROI state."""
#         super().set_model(model_id)
        
#         if self.model:
#             # Set initial ROI state
#             roi = self.model.roi
#             if roi and len(roi) == 2 and self.roi:
#                 self.roi.setRegion(roi)
            
#         if self.model and hasattr(self, 'show_roi_action') and self.show_roi_action:
#             roi_visible = self.model.roi_visible
#             self.roi_plot_area.setVisible(roi_visible)
#             self.show_roi_action.setChecked(roi_visible)
            
#             # Initial ROI plot update
#             self._roi_update_needed = True
#             self.roi_update_timer.start(100)
