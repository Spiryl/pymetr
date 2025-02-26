from typing import Dict, Any, Optional
from PySide6.QtWidgets import QVBoxLayout, QSplitter, QSizePolicy
from PySide6.QtCore import Qt, Slot, QTimer, QEvent
from PySide6.QtGui import QTransform
import pyqtgraph as pg
import numpy as np

from pymetr.ui.views.base import BaseWidget
from pymetr.core.logging import logger
from .trace_handler import TraceHandler
from .cursor_handler import CursorHandler
from .marker_handler import MarkerHandler

class PlotView(BaseWidget):
    """
    Enhanced PlotView with improved trace management, marker linking, and
    better legend positioning.
    
    Key improvements:
    1. Proper cleanup of isolated view boxes
    2. Legend positioned at top-left
    3. Autorange enabled by default
    4. Enhanced marker-to-trace linking
    5. Better ROI synchronization
    """

    def __init__(self, state, model_id: str, parent=None):
        logger.debug(f"Initializing PlotView with model_id: {model_id}")
        super().__init__(state, parent)
        self._suppress_roi_updates = False  # For ROI update loops

        # Mapping of trace id to ROI plot curve items for efficient updates
        self.roi_curves: Dict[str, pg.PlotDataItem] = {}

        # Initialize UI and handlers
        self._setup_ui()

        # Connect state signals with proper routing
        self.state.model_registered.connect(self._handle_model_registered)
        self.state.models_linked.connect(self._handle_model_linked)
        self.state.model_changed.connect(self._handle_model_changed)
        self.state.model_removed.connect(self._handle_model_removed)

        # Geometry update handling with debouncing (for ~60fps updates)
        self._geometry_update_timer = QTimer(self)
        self._geometry_update_timer.setSingleShot(True)
        self._geometry_update_timer.timeout.connect(self._update_geometries)
        self._geometry_update_needed = False

        # ROI update handling with debouncing (for ~20fps updates)
        self._roi_update_timer = QTimer(self)
        self._roi_update_timer.setSingleShot(True)
        self._roi_update_timer.timeout.connect(self._apply_roi_update)
        self._roi_connected = False  # Track ROI signal connection state

        # Set model to initialize handlers
        self.set_model(model_id)
        logger.debug("PlotView initialized")

    def _setup_ui(self) -> None:
        """Initialize the plot UI, main plot, ROI plot, and handlers."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Use a vertical splitter to hold the main plot and the ROI plot area
        self.plot_container = QSplitter(Qt.Vertical)
        layout.addWidget(self.plot_container)

        # --- Main Plot Setup ---
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_layout.setBackground('#1E1E1E')
        self.plot_container.addWidget(self.plot_layout)

        # Create main plot (renamed to main_plot_item for clarity)
        self.main_plot_item = self.plot_layout.addPlot(row=0, col=0)
        self.main_plot_item.setTitle("", size="20pt", color='w')
        
        # Enable autorange by default for main plot
        self.main_plot_item.enableAutoRange()

        # TODO: Legend should trace isolated traces as well or we need another legend to hold those. 
        try:
            # Create and position legend in top-left corner with better contrast
            self.legend = self.main_plot_item.addLegend(offset=(10, 10))
            if self.legend:
                # Make legend background semi-transparent black for better contrast
                self.legend.setBrush(pg.mkBrush(color=(50, 50, 50, 180)))
            logger.debug("Legend created in top-left corner")
        except Exception as e:
            logger.error(f"Legend creation failed: {e}")
            self.legend = None

        # Connect main plot range change to update ROI
        self.main_plot_item.scene().sigMouseClicked.connect(self.handle_mouse_clicked)
        self.main_plot_item.sigRangeChanged.connect(self._handle_main_plot_range_changed)

        # --- ROI Plot Setup ---
        self.roi_plot_area = pg.PlotWidget()
        self.roi_plot_area.setMinimumHeight(60)
        self.roi_plot_area.setMaximumHeight(60)
        self.roi_plot_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.roi_plot_area.setBackground('#2A2A2A')
        self.roi_plot_item = self.roi_plot_area.getPlotItem()
        self.roi_plot_item.showGrid(x=True, y=False)
        self.roi_plot_item.getAxis('left').hide()
        self.roi_plot_item.setMouseEnabled(x=False, y=False)
        bottom_axis = self.roi_plot_item.getAxis('bottom')
        bottom_axis.setPen(pg.mkPen('w'))
        bottom_axis.setTextPen(pg.mkPen('w'))

        # Add ROI selector with styling
        self.roi = pg.LinearRegionItem(
            brush=pg.mkBrush(color=(100, 100, 255, 50)),
            hoverBrush=pg.mkBrush(color=(100, 100, 255, 80)),
            movable=True
        )
        self.roi_plot_item.addItem(self.roi)
        self.roi.sigRegionChanged.connect(self._handle_roi_changed)

        # Add ROI plot area to the container
        self.plot_container.addWidget(self.roi_plot_area)


    def set_model(self, model_id: str) -> None:
        """
        Set the plot model and initialize all components.
        Extends BaseWidget.set_model to handle plot-specific initialization.
        """
        # Call base class implementation first
        super().set_model(model_id)
        
        if not self.model:
            logger.error(f"Failed to set model: {model_id}")
            return
            
        try:
            # Update basic plot settings
            self._initialize_plot()
            
            # Initialize handlers
            self.trace_handler = TraceHandler(self.main_plot_item, self.plot_layout)
            self.cursor_handler = CursorHandler(self.main_plot_item, self.state)
            self.marker_handler = MarkerHandler(self.main_plot_item, self.state)
            
            # Initialize existing traces
            for trace in self.model.get_traces():
                self.trace_handler.register_trace(trace)
                self._update_roi_curve(trace)
                logger.debug(f"Initialized trace {trace.id} during model set")
            
            # Initialize existing cursors
            for cursor in self.model.get_cursors():
                self.cursor_handler.register_cursor(cursor)
                logger.debug(f"Initialized cursor {cursor.id} during model set")
                
            # Initialize existing markers (checking if they're linked to traces)
            for marker in self.model.get_markers():
                # Check if marker is linked to a trace
                parent = self.state.get_parent(marker.id)
                if parent and parent.model_type == 'Trace':
                    # This marker is linked to a trace - set a flag
                    logger.debug(f"Marker {marker.id} is linked to trace {parent.id}")
                    marker.set_property('bound_to_trace', True)
                
                self.marker_handler.register_marker(marker)
                logger.debug(f"Initialized marker {marker.id} during model set")
                
            # Set initial ROI state if available
            roi = self.model.get_property("roi", None)
            if roi and len(roi) == 2:
                self.roi.setRegion(roi)
            
            # Set ROI visibility
            roi_visible = self.model.get_property("roi_visible", True)
            self.roi_plot_area.setVisible(roi_visible)
            
            # Queue an immediate ROI update
            self._queue_roi_update()
            
            # Initial auto-range to show all data
            QTimer.singleShot(100, self._initial_autorange)
                
        except Exception as e:
            logger.error(f"Error during plot model initialization: {e}")
    
    def _initial_autorange(self):
        """Perform initial auto-range after plot components are initialized."""
        try:
            self.main_plot_item.autoRange()
            # Auto-range isolated view boxes
            for view_box in getattr(self.trace_handler, 'isolated_view_boxes', {}).values():
                if view_box.scene():
                    view_box.enableAutoRange()
                    view_box.autoRange()
            logger.debug("Initial auto-range complete")
        except Exception as e:
            logger.error(f"Error during initial auto-range: {e}")

    def _is_descendant(self, model_id: str, ancestor_id: str) -> bool:
        """Return True if the model with model_id is a descendant of the model with ancestor_id."""
        current = self.state.get_parent(model_id)
        while current:
            if current.id == ancestor_id:
                return True
            current = self.state.get_parent(current.id)
        return False

    def _initialize_plot(self) -> None:
        """Update all plot settings from model."""
        if not self.model:
            return

        try:
            title = self.model.get_property('title', '')
            self.main_plot_item.setTitle(title, size="20pt", color='w')

            grid_enabled = self.model.get_property('grid_enabled', True)
            grid_alpha = self.model.get_property('grid_alpha', 0.3)
            self.main_plot_item.showGrid(x=grid_enabled, y=grid_enabled, alpha=grid_alpha)

            bg_color = self.model.get_property('background_color', '#1E1E1E')
            fg_color = self.model.get_property('foreground_color', '#FFFFFF')
            self.plot_layout.setBackground(bg_color)
            
            for axis in [self.main_plot_item.getAxis('left'), self.main_plot_item.getAxis('bottom')]:
                axis.setPen(pg.mkPen(fg_color))
                axis.setTextPen(pg.mkPen(fg_color))

            self._update_axis_labels()
            self._update_plot_ranges()

        except Exception as e:
            logger.error(f"Error updating plot settings: {e}")

    @Slot(str)
    def _handle_model_registered(self, model_id: str) -> None:
        try:
            model = self.state.get_model(model_id)
            if not model:
                logger.debug(f"Model {model_id} not found during registration")
                return

            # Process only if the model is the plot itself or a descendant of it.
            if model_id != self.model_id and not self._is_descendant(model_id, self.model_id):
                logger.debug(f"Model {model_id} is not a descendant of plot {self.model_id}")
                return

            logger.debug(f"Handling registration for model {model_id} (type: {model.model_type})")

            if model.model_type == "Marker":
                logger.debug(f"Registering Marker {model_id} via register_marker")
                self.marker_handler.register_marker(model)
            elif model.model_type == "Cursor":
                logger.debug(f"Registering Cursor {model_id} via register_cursor")
                self.cursor_handler.register_cursor(model)
            elif model.model_type == "Trace":
                logger.debug(f"Registering Trace {model_id}")
                self.trace_handler.register_trace(model)
                self._update_roi_curve(model)
                if self.roi_plot_area.isVisible():
                    self._queue_roi_update()
            else:
                logger.debug(f"No registration handler for model type {model.model_type} (model {model_id})")
        except Exception as e:
            logger.error(f"Error handling model registration for {model_id}: {e}", exc_info=True)


    @Slot(str, str, str, object)
    def _handle_model_changed(self, model_id: str, model_type: str, prop: str, value: any) -> None:
        try:
            # If the change is for the Plot itself, simply call change_plot()
            if model_id == self.model_id:
                logger.debug(f"Plot {model_id} changed property {prop} to {value}; calling change_plot()")
                self.change_plot(prop, value)
                return

            # Process changes only if the model is a descendant of this plot.
            if model_id != self.model_id and not self._is_descendant(model_id, self.model_id):
                logger.debug(f"Model {model_id} is not a descendant of plot {self.model_id}, ignoring change")
                return

            logger.debug(f"Handling change for model {model_id} (type: {model_type}): {prop}")

            if model_type == "Marker":
                logger.debug(f"Dispatching change_marker for Marker {model_id}")
                self.marker_handler.change_marker(model_id, prop, value)
            elif model_type == "Cursor":
                logger.debug(f"Dispatching change_cursor for Cursor {model_id}")
                self.cursor_handler.change_cursor(model_id, prop, value)
            elif model_type == "Trace":
                logger.debug(f"Dispatching change_trace for Trace {model_id}: {prop}")
                self.trace_handler.change_trace(model_id,  prop, value)
                trace_model = self.state.get_model(model_id)
                if trace_model:
                    self._update_roi_curve(trace_model)
                if self.roi_plot_area.isVisible():
                    self._queue_roi_update()
            else:
                logger.debug(f"No change handler for model type {model_type} (model {model_id})")
        except Exception as e:
            logger.error(f"Error handling model change for {model_id}: {e}", exc_info=True)


    @Slot(str, str)
    def _handle_model_linked(self, parent_id: str, child_id: str) -> None:
        try:
            # If the plot itself is the child, do nothing.
            if child_id == self.model_id:
                logger.debug(f"Plot {self.model_id} is the child in the link event; ignoring link for child {child_id}.")
                return

            # Process the event only if the parent is the plot itself or a descendant of the plot.
            if parent_id == self.model_id or self._is_descendant(parent_id, self.model_id):
                child_model = self.state.get_model(child_id)
                if not child_model:
                    logger.debug(f"Child model {child_id} not found during link handling.")
                    return

                logger.debug(f"Handling link event: parent {parent_id}, child {child_id} (type: {child_model.model_type})")
                if child_model.model_type == "Marker":
                    logger.debug(f"Linking Marker {child_id} via link_marker")
                    self.marker_handler.link_marker(child_model)
                elif child_model.model_type == "Cursor":
                    logger.debug(f"Linking Cursor {child_id} via link_cursor")
                    self.cursor_handler.link_cursor(child_model)
                elif child_model.model_type == "Trace":
                    logger.debug(f"Linking Trace {child_id} via link_trace")
                    self.trace_handler.link_trace(child_model)
                else:
                    logger.debug(f"No link handler for model type {child_model.model_type} (child {child_id})")
            else:
                logger.debug(f"Parent {parent_id} is not the plot {self.model_id} or a descendant; ignoring link event for child {child_id}.")
        except Exception as e:
            logger.error(f"Error handling model link for parent {parent_id} and child {child_id}: {e}", exc_info=True)

    @Slot(str)
    def _handle_model_removed(self, model_id: str) -> None:
        try:
            # Only process removal if the model is this plot or a descendant of it.
            if model_id != self.model_id and not self._is_descendant(model_id, self.model_id):
                logger.debug(f"Model {model_id} is not a descendant of plot {self.model_id}; ignoring removal")
                return

            # Delegate removal to each handler; each handler will handle non-existent models internally.
            self.marker_handler.remove_marker(model_id)
            self.trace_handler.remove_trace(model_id)
            self.cursor_handler.remove_cursor(model_id)
            logger.debug(f"Removed model {model_id} from all handlers")
        except Exception as e:
            logger.error(f"Error handling model removal for {model_id}: {e}", exc_info=True)


    def change_plot(self, prop: str, value: any) -> None:
        try:
            logger.debug(f"Change_plot called with {prop} = {value}")
            if prop == "background_color":
                self.plot_layout.setBackground(value)
                logger.debug(f"Updated background_color to {value}")
            elif prop == "grid_enabled":
                self.main_plot_item.showGrid(x=value, y=value, alpha=0.3)
                logger.debug(f"Updated grid_enabled to {value}")
            elif prop in ("x_lim", "y_lim", "x_inverted", "y_inverted", "x_log", "y_log"):
                self._update_plot_ranges()
                logger.debug("Updated plot ranges and scaling")
            elif prop in ("x_label", "y_label", "x_unit", "y_unit"):
                self._update_axis_labels()
                logger.debug("Updated axis labels")
            elif prop == "title":
                self.main_plot_item.setTitle(value, size="20pt", color='w')
                logger.debug(f"Updated title to {value}")
            elif prop == "roi":
                self.roi.setRegion(value)
                self._queue_roi_update()
                logger.debug(f"Updated ROI to {value}")
            elif prop == "roi_visible":
                self.roi_plot_area.setVisible(value)
                if value and not self._roi_connected:
                    self.roi.sigRegionChanged.connect(self._handle_roi_changed)
                    self._roi_connected = True
                    logger.debug("Connected ROI signal due to roi_visible True")
                elif not value and self._roi_connected:
                    try:
                        self.roi.sigRegionChanged.disconnect(self._handle_roi_changed)
                        logger.debug("Disconnected ROI signal due to roi_visible False")
                    except Exception:
                        logger.debug("Failed to disconnect ROI signal")
                    self._roi_connected = False
            else:
                logger.debug(f"No specific handler for plot property {prop}; ignoring.")
        except Exception as e:
            logger.error(f"Error in change_plot for property {prop}: {e}", exc_info=True)


    def _update_axis_labels(self) -> None:
        try:
            x_label = self.model.get_property('x_label', '')
            y_label = self.model.get_property('y_label', '')
            x_unit = self.model.get_property('x_unit', '')
            y_unit = self.model.get_property('y_unit', '')
            if x_unit:
                x_label = f"{x_label} ({x_unit})"
            if y_unit:
                y_label = f"{y_label} ({y_unit})"
            self.main_plot_item.setLabel('bottom', x_label)
            self.main_plot_item.setLabel('left', y_label)
            logger.debug(f"Axis labels updated to: bottom: {x_label}, left: {y_label}")
        except Exception as e:
            logger.error(f"Error updating axis labels: {e}", exc_info=True)


    def _update_plot_ranges(self) -> None:
        try:
            x_lim = self.model.get_property('x_lim')
            y_lim = self.model.get_property('y_lim')
            if x_lim is not None and isinstance(x_lim, (list, tuple)) and len(x_lim) == 2:
                self.main_plot_item.setXRange(x_lim[0], x_lim[1], padding=0)
            if y_lim is not None and isinstance(y_lim, (list, tuple)) and len(y_lim) == 2:
                self.main_plot_item.setYRange(y_lim[0], y_lim[1], padding=0)
            vb = self.main_plot_item.getViewBox()
            vb.invertX(self.model.get_property('x_inverted', False))
            vb.invertY(self.model.get_property('y_inverted', False))
            self.main_plot_item.setLogMode(
                x=self.model.get_property('x_log', False),
                y=self.model.get_property('y_log', False)
            )
            logger.debug("Plot ranges and scaling updated")
        except Exception as e:
            logger.error(f"Error updating plot ranges: {e}", exc_info=True)

    def _update_roi_curve(self, trace) -> None:
        try:
            trace_id = getattr(trace, 'id', None)
            if trace_id is None:
                logger.error("Trace has no id; skipping ROI curve update.")
                return

            if not self.roi_plot_area.isVisible():
                logger.debug("ROI plot area not visible; skipping ROI curve update.")
                return

            # Get the trace data: expecting a tuple (x_data, y_data)
            data = trace.data
            if not data or len(data) != 2:
                logger.error(f"Trace {trace_id} data is invalid; skipping ROI update.")
                return

            # Retrieve trace properties; if the trace supports get_property, use it, otherwise use attributes.
            color = trace.get_property('color', 'w') if hasattr(trace, 'get_property') else getattr(trace, 'color', 'w')
            width = trace.get_property('width', 1) if hasattr(trace, 'get_property') else getattr(trace, 'width', 1)
            style = trace.get_property('style', 'solid') if hasattr(trace, 'get_property') else getattr(trace, 'style', 'solid')
            visible = trace.get_property('visible', True) if hasattr(trace, 'get_property') else getattr(trace, 'visible', True)

            # Create a pen for the ROI curve; use the trace handler's helper for line style.
            pen = pg.mkPen(
                color=color,
                width=max(1, int(width) // 2),  # Make ROI curves slightly thinner
                style=self.trace_handler._get_qt_line_style(style)
            )

            # Update existing ROI curve or create a new one.
            if trace_id in self.roi_curves:
                roi_curve = self.roi_curves[trace_id]
                roi_curve.setData(data[0], data[1])
                roi_curve.setPen(pen)
                roi_curve.setVisible(visible)
                logger.debug(f"Updated ROI curve for trace {trace_id}")
            else:
                roi_curve = self.roi_plot_item.plot(
                    data[0],
                    data[1],
                    pen=pen,
                    name=str(trace_id)
                )
                roi_curve.setVisible(visible)
                self.roi_curves[trace_id] = roi_curve
                logger.debug(f"Created ROI curve for trace {trace_id}")
        except Exception as e:
            logger.error(f"Error updating ROI curve for trace {trace_id}: {e}", exc_info=True)

    def _queue_geometry_update(self) -> None:
        """Queue a geometry update with debouncing."""
        self._geometry_update_needed = True
        self._geometry_update_timer.start(16)  # ~60fps

    def _queue_roi_update(self) -> None:
        """Queue an ROI update with debouncing (~20fps)."""
        if not self._roi_update_timer.isActive():
            self._roi_update_timer.start(50)  # Reduced from 100ms for more responsive updates

    def _update_geometries(self) -> None:
        """Update geometries of all components."""
        if not self._geometry_update_needed:
            return
            
        try:
            rect = self.main_plot_item.getViewBox().sceneBoundingRect()
            self.trace_handler.update_geometry(rect)
            self.marker_handler.update_label_positions()
            self._geometry_update_needed = False
            
        except Exception as e:
            logger.error(f"Error updating geometries: {e}")

    def resizeEvent(self, event) -> None:
        """Handle widget resize efficiently."""
        super().resizeEvent(event)
        self._queue_geometry_update()

    def showEvent(self, event) -> None:
        """Handle widget show efficiently."""
        super().showEvent(event)
        self._queue_geometry_update()

    def clear(self) -> None:
        """Clean up all items and disconnect signals."""
        try:
            # Clean up handlers
            if hasattr(self, 'trace_handler'):
                self.trace_handler.clear_all()
            if hasattr(self, 'cursor_handler'):
                self.cursor_handler.clear_all()
            if hasattr(self, 'marker_handler'):
                self.marker_handler.clear_all()
            
            # Clean up timers
            self._geometry_update_timer.stop()
            self._roi_update_timer.stop()
            
            # Disconnect state signals
            try:
                self.state.model_registered.disconnect(self._handle_model_registered)
                self.state.model_changed.disconnect(self._handle_model_changed)
                self.state.model_removed.disconnect(self._handle_model_removed)
            except Exception:
                pass
            
            # Clean up ROI curves
            for curve in self.roi_curves.values():
                if curve.scene():
                    self.roi_plot_item.removeItem(curve)
            self.roi_curves.clear()
            
            logger.debug("PlotView cleared")

        except Exception as e:
            logger.error(f"Error clearing PlotView: {e}")

    def _handle_main_plot_range_changed(self, viewbox, ranges):
        """Update ROI when main plot range changes."""
        try:
            if self._suppress_roi_updates:
                return
            # Update the ROI region to match main plot's x-range
            self.roi.setRegion(ranges[0])
            self._queue_roi_update()  # Debounced ROI update
                
        except Exception as e:
            logger.error(f"Error in _handle_main_plot_range_changed: {e}")

    def _handle_roi_changed(self):
        """Handle ROI region changes immediately."""
        try:
            if not self.model or self._suppress_roi_updates:
                return
                
            region = self.roi.getRegion()
            region_list = [float(x) for x in region]
            
            if region_list != self.model.get_property('roi'):
                self.model.set_property('roi', region_list)
                self._suppress_roi_updates = True
                self.main_plot_item.setXRange(*region, padding=0)
                self._suppress_roi_updates = False
                
        except Exception as e:
            logger.error(f"Error handling ROI change: {e}")

    def _apply_roi_update(self):
        """Apply ROI updates by refreshing the ROI plot area with visible traces."""
        if not self.roi_plot_area.isVisible():
            return

        try:
            # Get all traces from the trace handler
            traces = []
            if hasattr(self, 'trace_handler'):
                traces = [tm for tm, _ in self.trace_handler.traces.values()]
            
            # Determine overall x-range from all traces
            x_ranges = []
            for trace in traces:
                data = trace.data  # Tuple (x_data, y_data)
                if data and data[0].size > 0:
                    x_ranges.append((np.nanmin(data[0]), np.nanmax(data[0])))
            
            # Set ROI plot x-range
            if x_ranges:
                x_min = min(r[0] for r in x_ranges if np.isfinite(r[0]))
                x_max = max(r[1] for r in x_ranges if np.isfinite(r[1]))
                if np.isfinite(x_min) and np.isfinite(x_max):
                    padding = (x_max - x_min) * 0.05
                    if padding == 0:  # Handle case of single value
                        padding = abs(x_min) * 0.1 if x_min != 0 else 0.1
                    self.roi_plot_item.setXRange(x_min - padding, x_max + padding, padding=0)

            # Update or create each ROI curve from traces
            for trace in traces:
                self._update_roi_curve(trace)

            # Ensure the ROI selector is present
            if self.roi not in self.roi_plot_item.items:
                self.roi_plot_item.addItem(self.roi)

        except Exception as e:
            logger.error(f"Error applying ROI update: {e}")

    def handle_mouse_clicked(self, event):
        """Handle mouse clicks for autoscaling."""
        if event.double():
            # Double click to auto-range the plot
            self.main_plot_item.autoRange()
            # Also auto-range any isolated view boxes
            if hasattr(self, 'trace_handler'):
                for view_box in self.trace_handler.isolated_view_boxes.values():
                    if view_box.scene():
                        view_box.autoRange()
                        view_box.enableAutoRange()
            logger.debug("Auto-ranged plot on double click")