# plot_view.py
from typing import Dict, Any
from PySide6.QtWidgets import QVBoxLayout, QSplitter
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QTransform
import pyqtgraph as pg
import numpy as np

from pymetr.views.widgets.base import BaseWidget
from pymetr.core.logging import logger
from pymetr.models import Plot, Trace, Cursor, Marker

class PlotView(BaseWidget):
    """
    PlotView displays a plot with support for multiple traces,
    cursors, markers, and isolated axes. It listens for model changes
    from the state and updates itself accordingly.
    """
    def __init__(self, state, model_id: str, parent=None):
        logger.debug("Initializing PlotView with model_id: %s", model_id)
        super().__init__(state, parent)
        
        # Dictionaries for visual elements
        self.traces: Dict[str, pg.PlotDataItem] = {}
        self.cursors: Dict[str, pg.InfiniteLine] = {}
        self.cursor_labels: Dict[str, pg.TextItem] = {}
        self.cursor_values: Dict[str, dict] = {}
        self.trace_view_boxes: Dict[str, pg.ViewBox] = {}
        self.trace_axes: Dict[str, pg.AxisItem] = {}
        self.additional_axes = []
        self.additional_view_boxes = []
        
        # Debounce geometry updates
        self._geometry_update_needed = False
        self.geometry_update_timer = QTimer(self)
        self.geometry_update_timer.setSingleShot(True)
        self.geometry_update_timer.timeout.connect(self._update_view_boxes)
        
        # Create UI
        self._setup_ui()
        
        # Connect state signals
        self.state.model_registered.connect(self._handle_model_registered)
        self.state.models_linked.connect(self._handle_models_linked)
        self.state.model_changed.connect(self._handle_model_changed)
        self.state.model_removed.connect(self._handle_model_removed)
        
        # Set model (which in turn will add traces, cursors, etc.)
        self.set_model(model_id)
        logger.debug("PlotView initialized.")

    def _setup_ui(self):
        """Initialize the plot UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Use a splitter for flexibility
        self.plot_container = QSplitter(Qt.Vertical)
        layout.addWidget(self.plot_container)
        
        # Create a GraphicsLayoutWidget for the plot
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_layout.setBackground('#1E1E1E')
        self.plot_container.addWidget(self.plot_layout)
        
        # Add a plot item (with default axes)
        self.plot_item = self.plot_layout.addPlot(row=0, col=0)
        self._setup_plot_area(self.plot_item)
        
        # Optionally add a legend (if desired)
        try:
            self.legend = self.plot_item.addLegend(offset=(70, 70))
            logger.debug("Legend created.")
        except Exception as e:
            logger.error("Legend creation failed: %s", e)
            self.legend = None
        
        # Set initial title
        self.plot_item.setTitle(title="", size="20pt", color='w')
        
        # Connect mouse events
        self.plot_item.scene().sigMouseClicked.connect(self._handle_mouse_clicked)
        self.plot_item.sigRangeChanged.connect(self._handle_main_plot_range_changed)
        
    def _setup_plot_area(self, plot_item: pg.PlotItem) -> pg.PlotItem:
        """Apply styling to the plot area."""
        plot_item.showGrid(x=True, y=True, alpha=0.3)
        for axis in [plot_item.getAxis('left'), plot_item.getAxis('bottom')]:
            axis.setPen(pg.mkPen('w'))
            axis.setTextPen(pg.mkPen('w'))
            axis.setStyle(tickTextOffset=5, tickLength=-10)
        return plot_item

    def set_model(self, model_id: str):
        """Set the plot model and initialize its children."""
        super().set_model(model_id)
        if self.model:
            # Apply initial plot settings
            self._update_plot_title(self.model.get_property("title", "Untitled Plot"))
            self._update_plot_settings()
            # If the plot model already has traces, cursors, or markers,
            # add them now. (Assuming your model has get_traces(), get_cursors(), etc.)
            for trace in self.model.get_traces():
                self._add_trace(trace)
            # Similarly for cursors:
            try:
                for cursor in self.model.get_cursors():
                    self._add_cursor(cursor)
            except Exception:
                pass  # If not implemented, ignore
            # And for markers (if applicable)
            logger.debug("Model properties applied in PlotView.")
        else:
            logger.error("No model found for model_id: %s", model_id)

    def _update_plot_title(self, title: str):
        """Update the plot title."""
        if hasattr(self, 'plot_item'):
            self.plot_item.setTitle(title=title, size="20pt", color='w')
            logger.debug("Plot title set to: %s", title)

    def _update_plot_settings(self):
        """Update settings like grid, colors, labels, and axis ranges."""
        if not self.model:
            logger.error("No model set when updating plot settings.")
            return

        grid_enabled = self.model.get_property("grid_enabled", True)
        grid_alpha = self.model.get_property("grid_alpha", 0.3)
        grid_color = self.model.get_property("grid_color", "#404040")
        self.plot_item.showGrid(x=grid_enabled, y=grid_enabled, alpha=grid_alpha)

        bg_color = self.model.get_property("background_color", "#1E1E1E")
        fg_color = self.model.get_property("foreground_color", "#FFFFFF")
        self.plot_layout.setBackground(bg_color)
        for axis in [self.plot_item.getAxis('left'), self.plot_item.getAxis('bottom')]:
            axis.setPen(pg.mkPen(fg_color))
            axis.setTextPen(pg.mkPen(fg_color))

        # Update legend if it exists
        if self.legend:
            legend_enabled = self.model.get_property("legend_enabled", True)
            legend_position = self.model.get_property("legend_position", "right")
            self.legend.setVisible(legend_enabled)
            offsets = {
                "right": (70, 70),
                "top": (70, 10),
                "bottom": (70, 120),
                "left": (10, 70)
            }
            self.legend.setOffset(offsets.get(legend_position, (70,70)))
        
        # Update axis labels
        x_label = self.model.get_property("x_label", "")
        y_label = self.model.get_property("y_label", "")
        x_unit = self.model.get_property("x_unit", "")
        y_unit = self.model.get_property("y_unit", "")
        if x_unit:
            x_label = f"{x_label} ({x_unit})"
        if y_unit:
            y_label = f"{y_label} ({y_unit})"
        self.plot_item.setLabel('bottom', x_label)
        self.plot_item.setLabel('left', y_label)

        # Use the viewbox to invert axes (since AxisItem lacks setInverted)
        vb = self.plot_item.getViewBox()
        vb.invertX(self.model.get_property("x_inverted", False))
        vb.invertY(self.model.get_property("y_inverted", False))
        
        # Set custom ticks if provided
        x_ticks = self.model.get_property("x_ticks", None)
        y_ticks = self.model.get_property("y_ticks", None)
        if x_ticks is not None:
            self.plot_item.getAxis('bottom').setTicks([[(t, str(t)) for t in x_ticks]])
        if y_ticks is not None:
            self.plot_item.getAxis('left').setTicks([[(t, str(t)) for t in y_ticks]])
        
        # Set axis ranges if provided
        x_lim = self.model.get_property("x_lim", None)
        y_lim = self.model.get_property("y_lim", None)
        if x_lim is not None:
            self.plot_item.setXRange(x_lim[0], x_lim[1], padding=0)
        if y_lim is not None:
            self.plot_item.setYRange(y_lim[0], y_lim[1], padding=0)
        
        logger.debug("Plot settings updated.")

    def _handle_model_registered(self, model_id: str):
        """Handle a new model registration by adding the corresponding view element."""
        model = self.state.get_model(model_id)
        if not model:
            return
        logger.debug("Model registered with ID: %s", model_id)
        if isinstance(model, Trace):
            self._add_trace(model)
        elif isinstance(model, Cursor):
            self._add_cursor(model)
        elif isinstance(model, Marker):
            self._add_marker(model)
        # Extend for other types as needed

    def _handle_models_linked(self, parent_id: str, child_id: str):
        """Handle new model links (if needed for nested plots/traces)."""
        # For example, if a Trace is linked to a Plot, you might want to add it:
        model = self.state.get_model(child_id)
        if isinstance(model, Trace):
            self._add_trace(model)
            logger.debug("Linked trace %s to parent %s", child_id, parent_id)

    def _handle_model_changed(self, model_id: str, prop: str, value: Any):
        """Dispatch changes from the model to the appropriate update handler."""
        logger.debug("Model changed: %s.%s = %s", model_id, prop, value)
        # Dispatch trace changes
        if model_id in self.traces:
            self._handle_trace_changed(model_id, prop, value)
        # Dispatch cursor changes
        elif model_id in self.cursors:
            self._handle_cursor_changed(model_id, prop, value)
        # Extend to markers, etc.

    def _handle_model_removed(self, model_id: str):
        """Clean up view elements when a model is removed."""
        if model_id in self.traces:
            self.plot_item.removeItem(self.traces[model_id])
            del self.traces[model_id]
            logger.debug("Removed trace %s", model_id)
        if model_id in self.cursors:
            self.plot_item.removeItem(self.cursors[model_id])
            if model_id in self.cursor_labels:
                self.plot_item.removeItem(self.cursor_labels[model_id])
                del self.cursor_labels[model_id]
            del self.cursors[model_id]
            logger.debug("Removed cursor %s", model_id)
        # Extend for markers, etc.

    def _handle_trace_changed(self, trace_id: str, prop: str, value: Any):
        """Update trace properties when the underlying model changes."""
        if trace_id not in self.traces:
            logger.error("Trace %s not found.", trace_id)
            return
        curve = self.traces[trace_id]
        if prop == "data":
            x_data, y_data = value
            curve.setData(x_data, y_data, connect='finite')
            logger.debug("Trace %s data updated.", trace_id)
        elif prop == "visible":
            curve.setVisible(value)
        elif prop == "color":
            pen = curve.opts['pen']
            pen.setColor(pg.mkColor(value))
            curve.setPen(pen)
        elif prop == "style":
            pen = curve.opts['pen']
            pen.setStyle(self._get_qt_line_style(value))
            curve.setPen(pen)
        elif prop == "width":
            pen = curve.opts['pen']
            pen.setWidth(value)
            curve.setPen(pen)
        # Add more property handling as needed

    def _handle_cursor_changed(self, cursor_id: str, prop: str, value: Any):
        """Update cursor properties based on model changes."""
        if cursor_id not in self.cursors:
            logger.error("Cursor %s not found.", cursor_id)
            return
        cursor_line = self.cursors[cursor_id]
        if prop == "position":
            cursor_line.setValue(value)
            self._update_cursor_values(cursor_id)
        elif prop == "color":
            pen = cursor_line.pen
            pen.setColor(pg.mkColor(value))
            cursor_line.setPen(pen)
            self._update_cursor_label(cursor_id)
        elif prop == "style":
            pen = cursor_line.pen
            pen.setStyle(self._get_qt_line_style(value))
            cursor_line.setPen(pen)
            self._update_cursor_label(cursor_id)
        elif prop == "width":
            pen = cursor_line.pen
            pen.setWidth(value)
            cursor_line.setPen(pen)
            self._update_cursor_label(cursor_id)
        elif prop == "visible":
            cursor_line.setVisible(value)
            self._update_cursor_label(cursor_id)
        logger.debug("Cursor %s updated: %s = %s", cursor_id, prop, value)

    def _get_qt_line_style(self, style_str: str) -> Qt.PenStyle:
        """Convert a string to a Qt pen style."""
        return {
            'solid': Qt.SolidLine,
            'dash': Qt.DashLine,
            'dot': Qt.DotLine,
            'dash-dot': Qt.DashDotLine
        }.get(style_str.lower(), Qt.SolidLine)

    def _add_trace(self, trace_model):
        """Add a new trace to the plot."""
        if trace_model.id in self.traces:
            logger.debug("Trace %s already exists.", trace_model.id)
            return
        logger.debug("Adding trace %s", trace_model.id)
        pen = pg.mkPen(
            color=trace_model.get_property('color', '#ffffff'),
            width=trace_model.get_property('width', 1),
            style=self._get_qt_line_style(trace_model.get_property('style', 'solid'))
        )
        curve = pg.PlotDataItem(
            trace_model.x_data,
            trace_model.y_data,
            pen=pen,
            name=trace_model.get_property('name', ''),
            connect='finite'
        )
        self.traces[trace_model.id] = curve
        # Add the trace to the main plot or to an isolated viewbox based on mode
        if trace_model.get_property('mode') == "Isolate":
            self.plot_item.removeItem(curve)
            self._setup_isolated_trace(trace_model, curve)
        else:
            self.plot_item.addItem(curve)
        curve.setVisible(trace_model.get_property('visible', True))
        logger.debug("Trace %s added successfully.", trace_model.id)

    def _setup_isolated_trace(self, trace_model, curve):
        """Create an isolated view for a trace."""
        color = trace_model.get_property('color', '#ffffff')
        pen = pg.mkPen(color=color)
        axis = pg.AxisItem("right", pen=pen)
        next_col = len(self.additional_axes) + 1
        self.plot_layout.addItem(axis, row=0, col=next_col)
        self.additional_axes.append(axis)
        self.trace_axes[trace_model.id] = axis
        view_box = pg.ViewBox()
        axis.linkToView(view_box)
        view_box.setXLink(self.plot_item.vb)
        self.plot_layout.scene().addItem(view_box)
        view_box.setGeometry(self.plot_item.vb.sceneBoundingRect())
        self.additional_view_boxes.append(view_box)
        self.trace_view_boxes[trace_model.id] = view_box
        view_box.addItem(curve)
        if trace_model.y_data.size:
            ymin, ymax = np.nanmin(trace_model.y_data), np.nanmax(trace_model.y_data)
            if np.isfinite(ymin) and np.isfinite(ymax):
                padding = (ymax - ymin) * 0.1
                view_box.setYRange(ymin - padding, ymax + padding)
        logger.debug("Isolated trace %s set up.", trace_model.id)

    def _add_cursor(self, cursor_model):
        """Add a cursor to the plot."""
        logger.debug("Adding cursor with ID: %s", cursor_model.id)
        if cursor_model.id in self.cursors:
            logger.debug("Cursor %s already exists.", cursor_model.id)
            return
        pos = cursor_model.get_property('position', 0.0)
        color = cursor_model.get_property('color', '#FFFF00')
        width = cursor_model.get_property('width', 1)
        style_str = cursor_model.get_property('style', 'solid')
        visible = cursor_model.get_property('visible', True)
        axis = cursor_model.get_property('axis', 'x')
        pen = pg.mkPen(color=color, width=width, style=self._get_qt_line_style(style_str))
        if axis == 'x':
            cursor_line = pg.InfiniteLine(pos, angle=90, movable=True, pen=pen)
        else:
            cursor_line = pg.InfiniteLine(pos, angle=0, movable=True, pen=pen)
        self.plot_item.addItem(cursor_line)
        cursor_line.setVisible(visible)
        label_item = pg.TextItem(text="", color=color, anchor=(0.5, 1))
        self.plot_item.addItem(label_item)
        label_item.setVisible(visible)
        self.cursors[cursor_model.id] = cursor_line
        self.cursor_labels[cursor_model.id] = label_item
        self.cursor_values[cursor_model.id] = {}
        # Connect movement signal to update handler
        cursor_line.sigPositionChanged.connect(lambda: self._handle_cursor_moved(cursor_model.id))
        self._update_cursor_values(cursor_model.id)
        logger.debug("Cursor %s added.", cursor_model.id)

    def _handle_cursor_moved(self, cursor_id: str):
        """When the user moves a cursor, update its model."""
        if cursor_id not in self.cursors:
            logger.error("Cursor %s not found during move.", cursor_id)
            return
        cursor_line = self.cursors[cursor_id]
        pos = cursor_line.value()
        cursor_model = self.state.get_model(cursor_id)
        if cursor_model:
            cursor_model.set_property('position', pos)
            logger.debug("Cursor model %s updated with new position: %s", cursor_id, pos)
        self._update_cursor_values(cursor_id)

    def _update_cursor_values(self, cursor_id: str):
        """Update values (e.g., from traces) for a given cursor and update its label."""
        if cursor_id not in self.cursors:
            logger.error("Cursor %s not found when updating values.", cursor_id)
            return
        cursor_line = self.cursors[cursor_id]
        pos = cursor_line.value()
        is_vertical = (cursor_line.angle == 90)
        values = {}
        for trace_id, curve in self.traces.items():
            if not curve.isVisible():
                continue
            data = curve.getData()
            if data[0].size == 0:
                continue
            if is_vertical:
                idx = np.abs(data[0] - pos).argmin()
                values[trace_id] = data[1][idx]
            else:
                idx = np.abs(data[1] - pos).argmin()
                values[trace_id] = data[0][idx]
        self.cursor_values[cursor_id] = values
        self._update_cursor_label(cursor_id)
        logger.debug("Cursor %s values updated: %s", cursor_id, values)

    def _update_cursor_label(self, cursor_id: str):
        """Update the label of a cursor with current values."""
        if cursor_id not in self.cursors or cursor_id not in self.cursor_labels:
            logger.error("Cursor or label missing for %s", cursor_id)
            return
        cursor_line = self.cursors[cursor_id]
        label_item = self.cursor_labels[cursor_id]
        values = self.cursor_values.get(cursor_id, {})
        if not values:
            label_item.setVisible(False)
            return
        lines = []
        for trace_id, val in values.items():
            trace_model = self.state.get_model(trace_id)
            trace_name = trace_model.get_property('name', trace_id) if trace_model else trace_id
            lines.append(f"{trace_name}: {val:.3f}")
        label_item.setText("\n".join(lines))
        # Position label relative to the cursor line
        if cursor_line.angle == 90:
            label_item.setPos(cursor_line.value(), max(values.values()))
        else:
            label_item.setPos(max(values.values()), cursor_line.value())
        label_item.setVisible(True)
        logger.debug("Cursor %s label updated.", cursor_id)

    def _add_marker(self, marker_model):
        """(Optional) Add a marker to the plot.
        This method can be implemented similarly to _add_cursor if needed.
        """
        logger.debug("Adding marker with ID: %s (not implemented)", marker_model.id)
        # Implement marker creation if markers are supported.

    @Slot(object, object)
    def _handle_main_plot_range_changed(self, viewbox, ranges):
        """Handle changes to the main plot range."""
        logger.debug("Main plot range changed: %s", ranges)
        # You might store or use the latest range here.

    def _handle_mouse_clicked(self, event):
        """Handle mouse clicks (e.g., for auto-ranging)."""
        if event.double():
            scene_point = event.scenePos()
            transform = QTransform()
            clicked_item = self.plot_item.scene().itemAt(scene_point, transform)
            # If clicking near an axis of an isolated trace, auto-range it.
            for trace_id, axis in self.trace_axes.items():
                if axis.boundingRect().contains(axis.mapFromScene(scene_point)):
                    if trace_id in self.trace_view_boxes:
                        self.trace_view_boxes[trace_id].autoRange(padding=0.1)
                        logger.debug("Auto-ranging isolated trace %s", trace_id)
                    return
            self.plot_item.autoRange(padding=0.1)
            logger.debug("Auto-ranging main plot.")

    def _update_view_boxes(self):
        """Update all isolated viewboxes when geometry changes."""
        if not self._geometry_update_needed:
            return
        main_rect = self.plot_item.vb.sceneBoundingRect()
        for view_box in self.additional_view_boxes:
            view_box.setGeometry(main_rect)
            view_box.linkedViewChanged(self.plot_item.vb, view_box.XAxis)
        self._geometry_update_needed = False
        logger.debug("Viewboxes updated.")

    def _queue_geometry_update(self):
        """Queue an update to viewbox geometries (debounced)."""
        self._geometry_update_needed = True
        self.geometry_update_timer.start(100)
        logger.debug("Geometry update queued.")

    def resizeEvent(self, event):
        """Handle widget resize events."""
        super().resizeEvent(event)
        self._queue_geometry_update()

    def showEvent(self, event):
        """Handle widget show events."""
        super().showEvent(event)
        self._queue_geometry_update()

    def clear(self):
        """Cleanup all plot items and disconnect signals."""
        logger.debug("Clearing PlotView...")
        try:
            self.state.model_registered.disconnect(self._handle_model_registered)
            self.state.models_linked.disconnect(self._handle_models_linked)
            self.state.model_changed.disconnect(self._handle_model_changed)
            self.state.model_removed.disconnect(self._handle_model_removed)
        except Exception as e:
            logger.error("Error disconnecting signals: %s", e)
        for curve in self.traces.values():
            self.plot_item.removeItem(curve)
        for cursor in self.cursors.values():
            self.plot_item.removeItem(cursor)
        for label in self.cursor_labels.values():
            self.plot_item.removeItem(label)
        self.traces.clear()
        self.cursors.clear()
        self.cursor_labels.clear()
        self.cursor_values.clear()
        logger.debug("PlotView cleared.")

    def closeEvent(self, event):
        """Clean up on widget close."""
        self.clear()
        super().closeEvent(event)
        logger.debug("PlotView closed.")



# from typing import Dict, Optional, Any
# from PySide6.QtWidgets import QVBoxLayout, QSplitter, QSizePolicy
# from PySide6.QtCore import Qt, QTimer, Slot, Signal
# from PySide6.QtGui import QTransform
# import pyqtgraph as pg
# import numpy as np

# from pymetr.views.widgets.base import BaseWidget
# from pymetr.core.logging import logger

# class PlotView(BaseWidget):
#     """Core plot visualization with comprehensive viewbox management."""
    
#     # Signals
#     traceVisibilityChanged = Signal(str, bool)  # trace_id, visible
#     traceModeChanged = Signal(str, str)         # trace_id, mode
#     viewBoxRangeChanged = Signal(str, tuple)    # trace_id, y_range
    
#     def __init__(self, state, model_id: str, parent=None):
#         super().__init__(state, parent)
        
#         # Core storage for plot components
#         self.traces: Dict[str, pg.PlotDataItem] = {}
#         self.trace_view_boxes: Dict[str, pg.ViewBox] = {}
#         self.trace_axes: Dict[str, pg.AxisItem] = {}
#         self.additional_axes = []
#         self.additional_view_boxes = []
        
#         # Legend management
#         self.legend = None
        
#         # Performance optimization flags
#         self._geometry_update_needed = False
#         self._suppress_updates = False
        
#         # Geometry update debouncing
#         self.geometry_update_timer = QTimer(self)
#         self.geometry_update_timer.setSingleShot(True)
#         self.geometry_update_timer.timeout.connect(self._update_view_boxes)
        
#         # Set up UI
#         self._setup_ui()
        
#         # Set model and connect signals
#         self.set_model(model_id)

#     def _setup_ui(self):
#         """Initialize plot UI components."""
#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)
        
#         # Main plot container
#         self.plot_container = QSplitter(Qt.Vertical)
#         layout.addWidget(self.plot_container)
        
#         # Create plot layout
#         self.plot_layout = pg.GraphicsLayoutWidget()
#         self.plot_layout.setBackground('#1E1E1E')
#         self.plot_container.addWidget(self.plot_layout)
        
#         # Main plot with axis items
#         self.plot_item = self.plot_layout.addPlot(row=0, col=0)
#         self._setup_plot_area(self.plot_item)
        
#         # Add title label with proper styling
#         self.plot_item.setTitle(title="", size="20pt", color='w')
        
#         # Create legend (hidden by default)
#         self.legend = self.plot_item.addLegend()
#         self.legend.hide()  # Will show based on model property
        
#         # Register mouse handlers
#         self.plot_item.scene().sigMouseClicked.connect(self._handle_mouse_clicked)
#         self.plot_item.sigRangeChanged.connect(self._handle_main_plot_range_changed)

#     def _setup_plot_area(self, plot_item: pg.PlotItem) -> pg.PlotItem:
#         """Configure plot area with proper styling."""
#         # Basic setup
#         plot_item.showGrid(x=True, y=True, alpha=0.3)
#         plot_item.setClipToView(True)
        
#         # Style axes
#         for axis in [plot_item.getAxis('left'), plot_item.getAxis('bottom')]:
#             axis.setPen(pg.mkPen('w'))
#             axis.setTextPen(pg.mkPen('w'))
#             axis.setStyle(tickTextOffset=5, tickLength=-10)
            
#         # Enable mouse interaction
#         plot_item.setMouseEnabled(x=True, y=True)
#         plot_item.enableAutoRange()
        
#         return plot_item

#     def _setup_isolated_trace(self, trace_model, curve: pg.PlotDataItem):
#         """Setup isolated trace with its own axis and viewbox."""
#         # Create axis with trace color
#         color = trace_model.get_property('color', '#ffffff')
#         pen = pg.mkPen(color=color)
#         axis = pg.AxisItem("right", pen=pen)
        
#         # Calculate position for new axis
#         next_col = len(self.additional_axes) + 1
#         self.plot_layout.addItem(axis, row=0, col=next_col)
#         self.additional_axes.append(axis)
#         self.trace_axes[trace_model.id] = axis
        
#         # Create and link viewbox
#         view_box = pg.ViewBox()
#         axis.linkToView(view_box)
#         view_box.setXLink(self.plot_item.vb)  # Link X axis to main plot
#         self.plot_layout.scene().addItem(view_box)
        
#         # Set initial geometry
#         view_box.setGeometry(self.plot_item.vb.sceneBoundingRect())
#         self.additional_view_boxes.append(view_box)
#         self.trace_view_boxes[trace_model.id] = view_box
        
#         # Move curve to new viewbox
#         if curve.getViewBox() == self.plot_item.vb:
#             self.plot_item.removeItem(curve)
#         view_box.addItem(curve)
        
#         # Set initial range if data exists
#         data = curve.getData()
#         if len(data[1]) > 0:
#             ymin, ymax = np.nanmin(data[1]), np.nanmax(data[1])
#             if np.isfinite(ymin) and np.isfinite(ymax):
#                 padding = (ymax - ymin) * 0.1
#                 view_box.setYRange(ymin - padding, ymax + padding)
        
#         # Connect viewbox signals
#         view_box.sigRangeChanged.connect(
#             lambda vb, ranges: self._handle_isolated_range_changed(trace_model.id, vb, ranges)
#         )
        
#         logger.debug(f"Setup isolated trace {trace_model.id} with new viewbox and axis")

#     def _cleanup_isolated_trace(self, trace_id: str, curve: pg.PlotDataItem):
#         """Clean up isolated trace components."""
#         if trace_id not in self.trace_view_boxes:
#             return
            
#         logger.debug(f"Cleaning up isolated trace {trace_id}")
        
#         # Get components
#         view_box = self.trace_view_boxes[trace_id]
#         axis = self.trace_axes[trace_id]
        
#         # Remove curve from viewbox
#         view_box.removeItem(curve)
        
#         # Add back to main plot
#         self.plot_item.addItem(curve)
        
#         # Clean up axis
#         if axis in self.additional_axes:
#             self.additional_axes.remove(axis)
#             self.plot_layout.removeItem(axis)
#             axis.deleteLater()
            
#         # Clean up viewbox
#         if view_box in self.additional_view_boxes:
#             self.additional_view_boxes.remove(view_box)
#             self.plot_layout.scene().removeItem(view_box)
#             view_box.deleteLater()
            
#         # Remove from storage
#         del self.trace_view_boxes[trace_id]
#         del self.trace_axes[trace_id]
        
#         # Queue geometry update
#         self._queue_geometry_update()
        
#         logger.debug(f"Cleaned up isolated trace {trace_id}")

#     def _handle_isolated_range_changed(self, trace_id: str, viewbox, ranges):
#         """Handle range changes in isolated viewboxes."""
#         if self._suppress_updates:
#             return
            
#         y_range = ranges[1]
#         self.viewBoxRangeChanged.emit(trace_id, y_range)
        
#         # Update any markers or cursors in this viewbox
#         self._update_markers_for_viewbox(trace_id)

#     def _update_view_boxes(self):
#         """Update all isolated viewbox geometries."""
#         if not self._geometry_update_needed:
#             return
            
#         main_rect = self.plot_item.vb.sceneBoundingRect()
#         for view_box in self.additional_view_boxes:
#             view_box.setGeometry(main_rect)
#             view_box.linkedViewChanged(self.plot_item.vb, view_box.XAxis)
            
#         self._geometry_update_needed = False

#     def _queue_geometry_update(self):
#         """Queue a geometry update with debouncing."""
#         self._geometry_update_needed = True
#         self.geometry_update_timer.start(100)

#     def resizeEvent(self, event):
#         """Handle widget resize events."""
#         super().resizeEvent(event)
#         self._queue_geometry_update()

#     def showEvent(self, event):
#         """Handle widget show events."""
#         super().showEvent(event)
#         self._queue_geometry_update()

#     @staticmethod
#     def _get_qt_line_style(style_str: str) -> Qt.PenStyle:
#         """Convert style string to Qt pen style."""
#         return {
#             'solid': Qt.SolidLine,
#             'dash': Qt.DashLine,
#             'dot': Qt.DotLine,
#             'dash-dot': Qt.DashDotLine
#         }.get(style_str.lower(), Qt.SolidLine)

#     def _handle_mouse_clicked(self, event):
#         """Handle mouse clicks for plot interaction."""
#         if event.double():
#             scene_point = event.scenePos()
#             transform = QTransform()
#             clicked_item = self.plot_item.scene().itemAt(scene_point, transform)
            
#             # Check if clicked on an isolated axis
#             for trace_id, axis in self.trace_axes.items():
#                 if axis.boundingRect().contains(axis.mapFromScene(scene_point)):
#                     if trace_id in self.trace_view_boxes:
#                         self.trace_view_boxes[trace_id].autoRange(padding=0.1)
#                         return
                    
#             # If not on an axis, autoscale main plot
#             self.plot_item.autoRange(padding=0.1)

#     def _add_trace(self, trace_model):
#         """Add a single trace to the plot with proper styling."""
#         if trace_model.id in self.traces:
#             return
            
#         logger.debug(f"Adding trace {trace_model.id}")
        
#         # Create curve with initial styling
#         pen = pg.mkPen(
#             color=trace_model.get_property('color', '#ffffff'),
#             width=trace_model.get_property('width', 1),
#             style=self._get_qt_line_style(trace_model.get_property('style', 'solid'))
#         )
        
#         curve = pg.PlotDataItem(
#             trace_model.x_data,
#             trace_model.y_data,
#             pen=pen,
#             name=trace_model.get_property('name', ''),
#             connect='finite'  # Handle NaN gaps properly
#         )
        
#         self.traces[trace_model.id] = curve
        
#         # Add to appropriate view based on mode
#         if trace_model.get_property('mode') == "Isolate":
#             self._setup_isolated_trace(trace_model, curve)
#         else:
#             self.plot_item.addItem(curve)
            
#         # Add to legend if enabled
#         if self.legend and self.model.get_property("legend_enabled", True):
#             self.legend.addItem(curve, trace_model.get_property('name', ''))
        
#         curve.setVisible(trace_model.get_property('visible', True))
#         logger.debug(f"Added trace {trace_model.id}")

#     def _update_trace_data(self, trace_id: str, x_data: np.ndarray, y_data: np.ndarray):
#         """Update trace data efficiently."""
#         if trace_id not in self.traces:
#             return
            
#         curve = self.traces[trace_id]
#         curve.setData(x_data, y_data, connect='finite')
        
#         # Update y-range for isolated traces
#         if trace_id in self.trace_view_boxes:
#             viewbox = self.trace_view_boxes[trace_id]
#             if len(y_data) > 0:
#                 ymin, ymax = np.nanmin(y_data), np.nanmax(y_data)
#                 if np.isfinite(ymin) and np.isfinite(ymax):
#                     padding = (ymax - ymin) * 0.1
#                     viewbox.setYRange(ymin - padding, ymax + padding)

#     def _update_trace_style(self, trace_id: str, prop: str, value: Any):
#         """Update trace visual properties efficiently."""
#         if trace_id not in self.traces:
#             return
            
#         curve = self.traces[trace_id]
        
#         if prop == 'color':
#             pen = curve.opts['pen']
#             pen.setColor(pg.mkColor(value))
#             curve.setPen(pen)
            
#             # Update axis color if isolated
#             if trace_id in self.trace_axes:
#                 self.trace_axes[trace_id].setPen(pg.mkPen(color=value))
                
#         elif prop == 'width':
#             pen = curve.opts['pen']
#             pen.setWidth(value)
#             curve.setPen(pen)
            
#         elif prop == 'style':
#             pen = curve.opts['pen']
#             pen.setStyle(self._get_qt_line_style(value))
#             curve.setPen(pen)
            
#         elif prop == 'visible':
#             curve.setVisible(value)
            
#         elif prop == 'name':
#             if self.legend:
#                 self.legend.removeItem(curve)
#                 self.legend.addItem(curve, value)

#     def _update_trace_mode(self, trace_id: str, mode: str):
#         """Handle trace mode changes (Group/Isolate)."""
#         if trace_id not in self.traces:
#             return
            
#         curve = self.traces[trace_id]
#         trace_model = self.state.get_model(trace_id)
#         if not trace_model:
#             return
            
#         if mode == "Isolate" and trace_id not in self.trace_view_boxes:
#             # Remove from main plot
#             self.plot_item.removeItem(curve)
#             self._setup_isolated_trace(trace_model, curve)
            
#         elif mode == "Group" and trace_id in self.trace_view_boxes:
#             self._cleanup_isolated_trace(trace_id, curve)
            
#         self.traceModeChanged.emit(trace_id, mode)

#     def _remove_trace(self, trace_id: str):
#         """Remove a trace with proper cleanup."""
#         if trace_id not in self.traces:
#             return
            
#         logger.debug(f"Removing trace {trace_id}")
        
#         curve = self.traces[trace_id]
        
#         # Remove from legend
#         if self.legend:
#             self.legend.removeItem(curve)
        
#         # Remove from appropriate viewbox
#         if trace_id in self.trace_view_boxes:
#             self._cleanup_isolated_trace(trace_id, curve)
#         else:
#             self.plot_item.removeItem(curve)
        
#         del self.traces[trace_id]
        
#         logger.debug(f"Removed trace {trace_id}")

#     def clear_traces(self):
#         """Remove all traces with proper cleanup."""
#         logger.debug("Clearing all traces")
        
#         # Clean up each trace
#         for trace_id in list(self.traces.keys()):
#             self._remove_trace(trace_id)
            
#         # Clear legend
#         if self.legend:
#             self.legend.clear()
            
#         # Ensure clean state
#         self.traces.clear()
#         self.trace_view_boxes.clear()
#         self.trace_axes.clear()
#         self.additional_axes.clear()
#         self.additional_view_boxes.clear()
        
#         # Update ROI plot
#         self._update_roi_plot()
        
#         logger.debug("All traces cleared")

#     def _setup_roi_plot(self):
#         """Setup the ROI plot area."""
#         logger.debug("Setting up ROI plot area")
        
#         # Create ROI plot widget
#         self.roi_plot_area = pg.PlotWidget()
#         self.roi_plot_area.setMinimumHeight(60)
#         self.roi_plot_area.setMaximumHeight(60)
#         self.roi_plot_area.setSizePolicy(
#             QSizePolicy.Expanding, 
#             QSizePolicy.Fixed
#         )
#         self.roi_plot_area.setBackground('#2A2A2A')
        
#         # Configure ROI plot
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
        
#         logger.debug("ROI plot area setup complete")

#     def _update_roi_plot(self):
#         """Update ROI plot with current trace data."""
#         logger.debug("Updating ROI plot")
#         try:
#             # Clear existing plots but keep ROI
#             self.roi_plot_item.clear()
#             self.roi_plot_item.addItem(self.roi)
            
#             # Calculate full data range
#             x_ranges = []
#             for trace_id, curve in self.traces.items():
#                 if curve.isVisible():
#                     data = curve.getData()
#                     if data[0].size > 0:
#                         x_ranges.extend([np.nanmin(data[0]), np.nanmax(data[0])])
            
#             if x_ranges:
#                 x_min, x_max = min(x_ranges), max(x_ranges)
#                 if np.isfinite(x_min) and np.isfinite(x_max):
#                     padding = (x_max - x_min) * 0.05
#                     self.roi_plot_item.setXRange(x_min - padding, x_max + padding, padding=0)
                    
#                     # Set ROI region if not already set
#                     if self.roi.getRegion() == (0, 1):
#                         self.roi.setRegion((x_min, x_max))
            
#             # Add visible traces to ROI plot
#             for trace_id, curve in self.traces.items():
#                 if curve.isVisible():
#                     data = curve.getData()
#                     self.roi_plot_item.plot(data[0], data[1], pen=curve.opts['pen'])
            
#             logger.debug("ROI plot update complete")
#         except Exception as e:
#             logger.error(f"Error updating ROI plot: {e}")

#     def _handle_roi_changed(self):
#         """Handle ROI region changes."""
#         if self._suppress_updates:
#             return
            
#         try:
#             region = self.roi.getRegion()
#             if not self.model:
#                 return
                
#             # Update model property
#             current_roi = self.model.get_property('roi')
#             region_list = [float(x) for x in region]
#             if region_list != current_roi:
#                 self.model.set_property('roi', region_list)
                
#                 # Update main plot range
#                 self._suppress_updates = True
#                 self.plot_item.setXRange(*region, padding=0)
#                 self._suppress_updates = False
                
#                 logger.debug(f"ROI region updated to {region_list}")
#         except Exception as e:
#             logger.error(f"Error handling ROI change: {e}")

#     @Slot(object, object)
#     def _handle_main_plot_range_changed(self, viewbox, ranges):
#         """Update ROI when main plot range changes."""
#         if self._suppress_updates:
#             return
            
#         try:
#             # Update ROI region
#             if self.roi:
#                 self.roi.setRegion(ranges[0])
                
#             # Store range for updates
#             self.latest_x_range = ranges[0]
            
#             # Update model property
#             if self.model:
#                 self.model.set_property('x_lim', list(ranges[0]))
                
#             logger.debug(f"Main plot range updated to {ranges[0]}")
#         except Exception as e:
#             logger.error(f"Error handling main plot range change: {e}")

#     def set_roi_visible(self, visible: bool):
#         """Show/hide ROI plot area."""
#         if hasattr(self, 'roi_plot_area'):
#             self.roi_plot_area.setVisible(visible)
#             logger.debug(f"ROI visibility set to {visible}")

#     def _handle_trace_property_changed(self, trace_id: str, prop: str, value: Any):
#         """Handle trace property changes that affect ROI."""
#         if prop in ['visible', 'data']:
#             self._update_roi_plot()

#     # --- Marker Management ---
#     def _setup_marker_storage(self):
#         """Initialize marker storage."""
#         self.markers: Dict[str, Dict[str, pg.ScatterPlotItem]] = {}  # marker_id -> {trace_id -> scatter}
#         self.marker_labels: Dict[str, pg.TextItem] = {}
        
#     def _add_marker(self, marker_model):
#         """Add a marker to the plot."""
#         if marker_model.id in self.markers:
#             return
            
#         # Create storage for this marker
#         self.markers[marker_model.id] = {}
        
#         # Get marker properties
#         color = marker_model.get_property('color', '#FFFF00')
#         size = marker_model.get_property('size', 8)
#         symbol = self._get_marker_symbol(marker_model.get_property('symbol', 'o'))
#         visible = marker_model.get_property('visible', True)
        
#         # Add marker to each visible trace
#         for trace_id, curve in self.traces.items():
#             if not curve.isVisible():
#                 continue
                
#             self._add_marker_to_trace(marker_model, trace_id, curve, color, size, symbol)
            
#         # Create label if specified
#         label = marker_model.get_property('label', '')
#         if label:
#             label_item = pg.TextItem(text=label, color=color, anchor=(0.5, 1))
#             self.marker_labels[marker_model.id] = label_item
#             self._update_marker_label_position(marker_model.id)

#     def _add_marker_to_trace(self, marker_model, trace_id, curve, color, size, symbol):
#         """Add marker to a specific trace."""
#         x_data = curve.xData
#         y_data = curve.yData
        
#         if len(x_data) == 0:
#             return
            
#         # Find marker position
#         x_pos = marker_model.get_property('x', 0.0)
        
#         # Find nearest data point
#         idx = np.abs(x_data - x_pos).argmin()
#         x_pos = x_data[idx]
#         y_pos = y_data[idx]
        
#         # Create scatter plot item
#         scatter = pg.ScatterPlotItem([x_pos], [y_pos], 
#                                    symbol=symbol, size=size,
#                                    pen=pg.mkPen(color), brush=pg.mkBrush(color))
        
#         # Add to appropriate viewbox
#         if trace_id in self.trace_view_boxes:
#             self.trace_view_boxes[trace_id].addItem(scatter)
#         else:
#             self.plot_item.addItem(scatter)
            
#         self.markers[marker_model.id][trace_id] = scatter

#     def _update_marker_position(self, marker_id: str, x_pos: float):
#         """Update marker position across all traces."""
#         if marker_id not in self.markers:
#             return
            
#         for trace_id, scatter in self.markers[marker_id].items():
#             if trace_id not in self.traces:
#                 continue
                
#             curve = self.traces[trace_id]
#             x_data = curve.xData
#             y_data = curve.yData
            
#             if len(x_data) == 0:
#                 continue
                
#             # Find nearest point
#             idx = np.abs(x_data - x_pos).argmin()
#             scatter.setData([x_data[idx]], [y_data[idx]])
            
#         self._update_marker_label_position(marker_id)

#     def _update_marker_style(self, marker_id: str, prop: str, value: Any):
#         """Update marker visual properties."""
#         if marker_id not in self.markers:
#             return
            
#         for scatter in self.markers[marker_id].values():
#             if prop == 'color':
#                 scatter.setPen(pg.mkPen(value))
#                 scatter.setBrush(pg.mkBrush(value))
#                 if marker_id in self.marker_labels:
#                     self.marker_labels[marker_id].setColor(value)
#             elif prop == 'size':
#                 scatter.setSize(value)
#             elif prop == 'symbol':
#                 scatter.setSymbol(self._get_marker_symbol(value))
#             elif prop == 'visible':
#                 scatter.setVisible(value)
#                 if marker_id in self.marker_labels:
#                     self.marker_labels[marker_id].setVisible(value)

#     def _update_marker_label_position(self, marker_id: str):
#         """Update marker label position."""
#         if marker_id not in self.marker_labels:
#             return
            
#         label_item = self.marker_labels[marker_id]
        
#         # Find first visible marker to position label
#         for scatter in self.markers[marker_id].values():
#             if scatter.isVisible():
#                 pos = scatter.data['pos'][0]
#                 label_item.setPos(pos[0], pos[1])
#                 return

#     def _remove_marker(self, marker_id: str):
#         """Remove a marker from all traces."""
#         if marker_id not in self.markers:
#             return
            
#         # Remove scatter items
#         for trace_id, scatter in self.markers[marker_id].items():
#             if trace_id in self.trace_view_boxes:
#                 self.trace_view_boxes[trace_id].removeItem(scatter)
#             else:
#                 self.plot_item.removeItem(scatter)
                
#         # Remove label if it exists
#         if marker_id in self.marker_labels:
#             label_item = self.marker_labels[marker_id]
#             if label_item.scene() is not None:
#                 label_item.scene().removeItem(label_item)
#             del self.marker_labels[marker_id]
            
#         del self.markers[marker_id]

#     @staticmethod
#     def _get_marker_symbol(symbol: str) -> str:
#         """Convert symbol string to PyQtGraph symbol."""
#         return {
#             'o': 'o',  # circle
#             't': 't',  # triangle
#             's': 's',  # square
#             'd': 'd',  # diamond
#         }.get(symbol, 'o')  # default to circle

#     def _update_markers_for_viewbox(self, trace_id: str):
#         """Update markers when trace viewbox changes."""
#         viewbox = self.trace_view_boxes.get(trace_id) or self.plot_item.vb
        
#         for marker_id, markers in self.markers.items():
#             if trace_id in markers:
#                 scatter = markers[trace_id]
#                 current_vb = scatter.getViewBox()
                
#                 # Move to new viewbox if needed
#                 if current_vb != viewbox:
#                     if current_vb:
#                         current_vb.removeItem(scatter)
#                     viewbox.addItem(scatter)
                    
#                 self._update_marker_label_position(marker_id)

#     # --- Cursor Management ---
#     def _setup_cursor_storage(self):
#         """Initialize cursor storage."""
#         self.cursors: Dict[str, pg.InfiniteLine] = {}
#         self.cursor_labels: Dict[str, pg.TextItem] = {}
#         self.cursor_values: Dict[str, Dict[str, float]] = {}  # cursor_id -> {trace_id -> value}
        
#     def _add_cursor(self, cursor_model):
#         """Add a cursor to the plot."""
#         if cursor_model.id in self.cursors:
#             return
            
#         # Get cursor properties
#         pos = cursor_model.get_property('position', 0.0)
#         color = cursor_model.get_property('color', '#FFFF00')
#         width = cursor_model.get_property('width', 1)
#         style = self._get_qt_line_style(cursor_model.get_property('style', 'solid'))
#         visible = cursor_model.get_property('visible', True)
#         axis = cursor_model.get_property('axis', 'x')
        
#         # Create cursor line
#         pen = pg.mkPen(color=color, width=width, style=style)
#         if axis == 'x':
#             cursor_line = pg.InfiniteLine(pos, angle=90, movable=True, pen=pen)
#         else:
#             cursor_line = pg.InfiniteLine(pos, angle=0, movable=True, pen=pen)
            
#         # Add to main plot (cursors always stay in main viewbox)
#         self.plot_item.addItem(cursor_line)
#         cursor_line.setVisible(visible)
        
#         # Create value label
#         label_item = pg.TextItem(color=color, anchor=(0.5, 1))
#         self.plot_item.addItem(label_item)
#         label_item.setVisible(visible)
        
#         # Store cursor components
#         self.cursors[cursor_model.id] = cursor_line
#         self.cursor_labels[cursor_model.id] = label_item
#         self.cursor_values[cursor_model.id] = {}
        
#         # Connect movement signal
#         cursor_line.sigPositionChanged.connect(
#             lambda: self._handle_cursor_moved(cursor_model.id)
#         )
        
#         # Initial value update
#         self._update_cursor_values(cursor_model.id)

#     def _update_cursor_values(self, cursor_id: str):
#         """Update values for all traces at cursor position."""
#         if cursor_id not in self.cursors:
#             return
            
#         cursor = self.cursors[cursor_id]
#         cursor_pos = cursor.value()
#         is_vertical = (cursor.angle == 90)
        
#         values = {}
#         for trace_id, curve in self.traces.items():
#             if not curve.isVisible():
#                 continue
                
#             x_data = curve.xData
#             y_data = curve.yData
            
#             if len(x_data) == 0:
#                 continue
                
#             if is_vertical:
#                 # Find nearest x point
#                 idx = np.abs(x_data - cursor_pos).argmin()
#                 values[trace_id] = y_data[idx]
#             else:
#                 # Find nearest y point
#                 idx = np.abs(y_data - cursor_pos).argmin()
#                 values[trace_id] = x_data[idx]
        
#         self.cursor_values[cursor_id] = values
#         self._update_cursor_label(cursor_id)

#     def _update_cursor_label(self, cursor_id: str):
#         """Update cursor label with current values."""
#         if cursor_id not in self.cursors or cursor_id not in self.cursor_labels:
#             return
            
#         cursor = self.cursors[cursor_id]
#         label = self.cursor_labels[cursor_id]
#         values = self.cursor_values[cursor_id]
        
#         if not values:
#             label.setVisible(False)
#             return
            
#         # Format values into label text
#         lines = []
#         for trace_id, value in values.items():
#             trace_model = self.state.get_model(trace_id)
#             if trace_model:
#                 trace_name = trace_model.get_property('name', trace_id)
#                 lines.append(f"{trace_name}: {value:.3f}")
                
#         label.setText('\n'.join(lines))
        
#         # Position label near cursor
#         cursor_pos = cursor.value()
#         if cursor.angle == 90:  # Vertical cursor
#             # Position above highest point
#             y_pos = max(values.values())
#             label.setPos(cursor_pos, y_pos)
#         else:  # Horizontal cursor
#             # Position right of rightmost point
#             x_pos = max(values.values())
#             label.setPos(x_pos, cursor_pos)
            
#         label.setVisible(True)

#     def _handle_cursor_moved(self, cursor_id: str):
#         """Handle cursor movement by user."""
#         if not self._suppress_updates:
#             cursor = self.cursors[cursor_id]
#             pos = cursor.value()
            
#             # Update model
#             cursor_model = self.state.get_model(cursor_id)
#             if cursor_model:
#                 cursor_model.set_property('position', pos)
                
#             # Update values and label
#             self._update_cursor_values(cursor_id)

#     def _update_cursor_style(self, cursor_id: str, prop: str, value: Any):
#         """Update cursor visual properties."""
#         if cursor_id not in self.cursors:
#             return
            
#         cursor = self.cursors[cursor_id]
#         label = self.cursor_labels.get(cursor_id)
        
#         if prop == 'color':
#             pen = cursor.pen
#             pen.setColor(pg.mkColor(value))
#             cursor.setPen(pen)
#             if label:
#                 label.setColor(value)
#         elif prop == 'width':
#             pen = cursor.pen
#             pen.setWidth(value)
#             cursor.setPen(pen)
#         elif prop == 'style':
#             pen = cursor.pen
#             pen.setStyle(self._get_qt_line_style(value))
#             cursor.setPen(pen)
#         elif prop == 'visible':
#             cursor.setVisible(value)
#             if label:
#                 label.setVisible(value and bool(self.cursor_values[cursor_id]))
#         elif prop == 'position':
#             self._suppress_updates = True
#             cursor.setValue(value)
#             self._update_cursor_values(cursor_id)
#             self._suppress_updates = False

#     def _remove_cursor(self, cursor_id: str):
#         """Remove a cursor from the plot."""
#         if cursor_id not in self.cursors:
#             return
            
#         # Remove cursor line
#         cursor = self.cursors[cursor_id]
#         self.plot_item.removeItem(cursor)
        
#         # Remove label
#         if cursor_id in self.cursor_labels:
#             label = self.cursor_labels[cursor_id]
#             self.plot_item.removeItem(label)
#             del self.cursor_labels[cursor_id]
            
#         # Clean up storage
#         del self.cursors[cursor_id]
#         if cursor_id in self.cursor_values:
#             del self.cursor_values[cursor_id]

#     def get_cursor_values(self, cursor_id: str) -> Dict[str, float]:
#         """Get current values for all traces at cursor position."""
#         return self.cursor_values.get(cursor_id, {})
