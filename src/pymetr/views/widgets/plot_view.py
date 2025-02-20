from typing import Dict, Any
from PySide6.QtWidgets import QVBoxLayout, QSplitter, QSizePolicy
from PySide6.QtCore import Qt, Slot, QTimer, QEvent
from PySide6.QtGui import QTransform
import pyqtgraph as pg
import numpy as np

from pymetr.views.widgets.base import BaseWidget
from pymetr.core.logging import logger
from .trace_handler import TraceHandler
from .cursor_handler import CursorHandler
from .marker_handler import MarkerHandler

class PlotView(BaseWidget):
    """
    Enhanced PlotView that efficiently routes model updates to specialized handlers.
    Coordinates real-time updates between traces, cursors, and markers.
    """

    def __init__(self, state, model_id: str, parent=None):
        logger.debug(f"Initializing PlotView with model_id: {model_id}")
        super().__init__(state, parent)
        self._suppress_roi_updates = False  # For ROI update loops

        # Mapping of trace id to ROI plot curve items for efficient updates.
        self.roi_curves: Dict[str, pg.PlotDataItem] = {}

        # Initialize UI and handlers
        self._setup_ui()

        # Connect state signals with proper routing
        self.state.model_registered.connect(self._handle_model_registered)
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
        try:
            self.legend = self.main_plot_item.addLegend(offset=(70, 70))
            logger.debug("Legend created")
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

    def handle_mouse_clicked(self, event):
        """Handle mouse clicks for autoscaling."""
        if event.double():
            # scene_point = event.scenePos()
            # # transform = QTransform()
            # # clicked_item = self.main_plot_itemplot_item.scene().itemAt(scene_point, transform)
            
            # # Check if clicked on an isolated axis
            # for trace_id, axis in self.trace_axes.items():
            #     if axis.boundingRect().contains(axis.mapFromScene(scene_point)):
            #         if trace_id in self.trace_view_boxes:
            #             self.trace_view_boxes[trace_id].autoRange(padding=0)
            #         return
                    
            # If not on an axis, autoscale main plot
            self.main_plot_item.autoRange()

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
            self._update_plot_settings()
            
            # Initialize handlers TODO: Clean this up?  Why is the pattern different?
            self.trace_handler = TraceHandler(self.main_plot_item, self.plot_layout)
            self.cursor_handler = CursorHandler(self.main_plot_item, self.state)
            self.marker_handler = MarkerHandler(self.main_plot_item, self.state)
            
            # Initialize existing traces
            for trace in self.model.get_traces():
                self.trace_handler.add_trace(trace)
                self._create_or_update_roi_curve(trace)
                logger.debug(f"Initialized trace {trace.id} during model set")
            
            # Initialize existing cursors
            for cursor in self.model.get_cursors():
                self.cursor_handler.add_cursor(cursor)
                logger.debug(f"Initialized cursor {cursor.id} during model set")
                
            # Initialize existing markers
            for marker in self.model.get_markers():
                self.marker_handler.add_marker(marker)
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
                
        except Exception as e:
            logger.error(f"Error during plot model initialization: {e}")

    def _is_descendant(self, model_id: str, ancestor_id: str) -> bool:
        """Return True if the model with model_id is a descendant of the model with ancestor_id."""
        current = self.state.get_parent(model_id)
        while current:
            if current.id == ancestor_id:
                return True
            current = self.state.get_parent(current.id)
        return False

    @Slot(str, str, str, object)
    def _handle_model_changed(self, model_id: str, model_type: str, prop: str, value: Any) -> None:
        """
        Handle property changes. We only process changes for:
        - This Plot itself (model_id == self.model_id)
        - A Trace/Cursor/Marker whose *immediate* parent is this Plot.
        """
        try:

            if model_id == self.model_id and model_type == "Plot":
                # This is the Plot itself
                if prop == 'roi':
                    self._suppress_roi_updates = True
                    self.roi.setRegion(value)
                    self.main_plot_item.setXRange(*value, padding=0)
                    self._suppress_roi_updates = False
                    self._queue_roi_update()  # Debounced update
                elif prop == 'roi_visible':
                    self.roi_plot_area.setVisible(value)
                    if value and not self._roi_connected:
                        self.roi.sigRegionChanged.connect(self._handle_roi_changed)
                        self._roi_connected = True
                    elif not value and self._roi_connected:
                        try:
                            self.roi.sigRegionChanged.disconnect(self._handle_roi_changed)
                        except Exception:
                            pass
                        self._roi_connected = False
                else:
                    self._handle_plot_property_change(prop, value)
                return

            # For traces, cursors, markers: only update if I'm their *immediate* parent
            if model_type in ("Trace", "Cursor", "Marker"):
                parent = self.state.get_parent(model_id)
                if parent and parent.id == self.model_id:
                    if model_type == "Trace":
                        self.trace_handler.handle_property_change(model_id, model_type, prop, value)
                        trace_model = self.state.get_model(model_id)
                        if trace_model:
                            self._create_or_update_roi_curve(trace_model)
                        if self.roi_plot_area.isVisible():
                            self._queue_roi_update()  # Debounced update
                    elif model_type == "Cursor":
                        self.cursor_handler.handle_property_change(model_id, model_type, prop, value)
                    elif model_type == "Marker":
                        self.marker_handler.handle_property_change(model_id, model_type, prop, value)
                return

        except Exception as e:
            logger.error(f"Error handling model change: {e}")


    @Slot(str)
    def _handle_model_registered(self, model_id: str) -> None:
        """
        Handle new model registration. Only add it if its *immediate* parent is this Plot.
        """
        try:
            model = self.state.get_model(model_id)
            if not model:
                return

            if model.model_type in ("Trace", "Cursor", "Marker"):
                parent = self.state.get_parent(model_id)
                if parent and parent.id == self.model_id:
                    if model.model_type == "Trace":
                        self.trace_handler.add_trace(model)
                        self._create_or_update_roi_curve(model)
                        if self.roi_plot_area.isVisible():
                            self._queue_roi_update()
                    elif model.model_type == "Cursor":
                        self.cursor_handler.add_cursor(model)
                    elif model.model_type == "Marker":
                        self.marker_handler.add_marker(model)

        except Exception as e:
            logger.error(f"Error handling model registration: {e}")


    @Slot(str)
    def _handle_model_removed(self, model_id: str) -> None:
        """
        Remove a model from the appropriate handler if I'm its *immediate* parent.
        """
        try:
            # If it's in the trace handler
            if model_id in getattr(self.trace_handler, 'traces', {}):
                parent = self.state.get_parent(model_id)
                if parent and parent.id == self.model_id:
                    self.trace_handler.remove_trace(model_id)
                    if model_id in self.roi_curves:
                        self.roi_plot_item.removeItem(self.roi_curves[model_id])
                        del self.roi_curves[model_id]

            # If it's in the cursor handler
            elif model_id in getattr(self.cursor_handler, 'cursors', {}):
                parent = self.state.get_parent(model_id)
                if parent and parent.id == self.model_id:
                    self.cursor_handler.remove_cursor(model_id)

            # If it's in the marker handler
            elif model_id in getattr(self.marker_handler, 'markers', {}):
                parent = self.state.get_parent(model_id)
                if parent and parent.id == self.model_id:
                    self.marker_handler.remove_marker(model_id)

        except Exception as e:
            logger.error(f"Error handling model removal: {e}")

    def _handle_plot_property_change(self, prop: str, value: Any) -> None:
        """Handle plot-specific property changes."""
        try:
            if prop == "background_color":
                self.plot_layout.setBackground(value)
            elif prop == "grid_enabled":
                self.main_plot_item.showGrid(x=value, y=value, alpha=0.3)
            elif prop == "x_lim":  # Changed from x_range to x_lim
                if value and isinstance(value, (list, tuple)) and len(value) == 2:
                    self.main_plot_item.setXRange(value[0], value[1], padding=0)
            elif prop == "y_lim":  # Changed from y_range to y_lim
                if value and isinstance(value, (list, tuple)) and len(value) == 2:
                    self.main_plot_item.setYRange(value[0], value[1], padding=0)
            elif prop == "title":
                self.main_plot_item.setTitle(value, size="20pt", color='w')
        except Exception as e:
            logger.error(f"Error handling plot property change: {e}")

    def _update_plot_settings(self) -> None:
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

    def _update_axis_labels(self) -> None:
        """Update axis labels and units."""
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

        except Exception as e:
            logger.error(f"Error updating axis labels: {e}")

    def _update_plot_ranges(self) -> None:
        """Update plot ranges and scaling."""
        try:
            x_lim = self.model.get_property('x_lim')  # Changed from x_range to x_lim
            y_lim = self.model.get_property('y_lim')  # Changed from y_range to y_lim
            
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
        except Exception as e:
            logger.error(f"Error updating plot ranges: {e}")

    def _queue_geometry_update(self) -> None:
        """Queue a geometry update with debouncing."""
        self._geometry_update_needed = True
        self._geometry_update_timer.start(16)  # ~60fps

    def _queue_roi_update(self) -> None:
        """Queue an ROI update with debouncing (~20fps)."""
        if not self._roi_update_timer.isActive():
            self._roi_update_timer.start(100)

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
            self.trace_handler.clear_all()
            self.cursor_handler.clear_all()
            self.marker_handler.clear_all()
            
            self._geometry_update_timer.stop()
            self._roi_update_timer.stop()
            
            try:
                self.state.model_registered.disconnect(self._handle_model_registered)
                self.state.model_changed.disconnect(self._handle_model_changed)
                self.state.model_removed.disconnect(self._handle_model_removed)
            except Exception:
                pass
            
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
        """Apply ROI updates by refreshing the ROI plot area with visible traces.
        
        Only update if the ROI plot area is visible and only for traces associated
        with this plot view instance.
        """
        if not self.roi_plot_area.isVisible():
            return

        try:
            # Iterate over traces stored in the trace handler (each is a (model, curve) tuple)
            traces = [tm for tm, curve in self.trace_handler.traces.values()]
            
            # Determine overall x-range using the trace model's data
            x_ranges = []
            for trace in traces:
                data = trace.data  # Assuming trace.data is a tuple (x_data, y_data)
                if data[0].size > 0:
                    x_ranges.append((np.nanmin(data[0]), np.nanmax(data[0])))
            if x_ranges:
                x_min = min(r[0] for r in x_ranges)
                x_max = max(r[1] for r in x_ranges)
                if np.isfinite(x_min) and np.isfinite(x_max):
                    padding = (x_max - x_min) * 0.05
                    self.roi_plot_item.setXRange(x_min - padding, x_max + padding, padding=0)

            # Update or create each ROI curve using the trace model.
            for trace in traces:
                self._create_or_update_roi_curve(trace)

            # Ensure the ROI selector is present.
            if self.roi not in self.roi_plot_item.items:
                self.roi_plot_item.addItem(self.roi)

        except Exception as e:
            logger.error(f"Error applying ROI update for model {self.model_id}: {e}")

    def _create_or_update_roi_curve(self, trace) -> None:
        """
        Create or update an ROI curve for a trace belonging to this plot view instance.
        """
        trace_id = getattr(trace, 'model_id', None) or getattr(trace, 'id', None)
        if trace_id is None:
            logger.error("Trace has no model_id or id; skipping ROI update.")
            return

        # Skip if ROI plot area is not visible
        if not self.roi_plot_area.isVisible():
            # logger.debug(
            #     f"ROI plot area is not visible for model: {self.model_id}. "
            #     f"Skipping ROI curve update for trace '{trace_id}'."
            # )
            return

        # logger.debug(f"Creating/updating ROI curve for trace '{trace_id}' in model: {self.model_id}")

        try:
            # Use the trace model to get data and properties
            data = trace.data  # (x_data, y_data)
            color = trace.color if trace.color is not None else 'w'
            width = trace.width
            style = trace.style
            pen = pg.mkPen(color=color, width=width, style=TraceHandler._get_qt_line_style(style))
            visible = trace.visible

            if trace_id in self.roi_curves:
                roi_curve = self.roi_curves[trace_id]
                roi_curve.setData(data[0], data[1])
                roi_curve.setPen(pen)
                roi_curve.setVisible(visible)
            else:
                roi_curve = self.roi_plot_area.plot(
                    data[0],
                    data[1],
                    pen=pen,
                    name=str(trace_id)
                )
                roi_curve.setVisible(visible)
                self.roi_curves[trace_id] = roi_curve

        except Exception as e:
            logger.error(f"Error in _create_or_update_roi_curve for trace '{trace_id}' in model {self.model_id}: {e}")
