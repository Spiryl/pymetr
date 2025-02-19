from PySide6.QtCore import QObject, Qt
import pyqtgraph as pg
import numpy as np
from typing import Dict, Any, Tuple
from pymetr.core.logging import logger

class TraceHandler(QObject):
    """
    High-performance trace handler optimized for real-time visualization.
    Manages trace rendering with minimal overhead and efficient updates.
    """
    
    def __init__(self, plot_item: pg.PlotItem, plot_layout: pg.GraphicsLayoutWidget):
        super().__init__()
        self.plot_item = plot_item
        self.plot_layout = plot_layout
        
        # Now store a tuple: (trace_model, curve)
        self.traces: Dict[str, Tuple[Any, pg.PlotDataItem]] = {}
        self.isolated_axes: Dict[str, pg.AxisItem] = {}
        self.isolated_view_boxes: Dict[str, pg.ViewBox] = {}

        # Fast-path flags
        self._suppress_updates = False
        self._last_thread = None
        
        logger.debug("TraceHandler initialized")

    def add_trace(self, trace_model) -> None:
        """Add a new trace from model."""
        trace_id = trace_model.id
        if trace_id in self.traces:
            return

        try:
            # Create curve with initial properties
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

            # Store the trace model and curve together.
            self.traces[trace_id] = (trace_model, curve)
            
            # Handle isolation mode
            if trace_model.get_property('mode') == "Isolate":
                self._setup_isolated_view(trace_id, curve, trace_model)
            else:
                self.plot_item.addItem(curve)

            # Set initial visibility
            curve.setVisible(trace_model.get_property('visible', True))
            logger.debug(f"Added trace {trace_id}")

        except Exception as e:
            logger.error(f"Error adding trace {trace_id}: {e}")
            self.remove_trace(trace_id)

    # ... other methods remain largely the same, but note that
    # whenever you need to update a trace, you now first fetch the tuple.
    
    def handle_property_change(self, model_id: str, model_type: str, prop: str, value: Any) -> None:
        """Fast property change handler optimized for high-frequency updates."""
        if model_type != 'Trace' or model_id not in self.traces:
            return

        try:
            trace_model, curve = self.traces[model_id]
            if prop == "data":
                self._fast_update_data(model_id, value)
            elif prop == "color":
                self._update_color(model_id, value)
            elif prop == "visible":
                self._update_visibility(model_id, value)
            elif prop in ("width", "style"):
                self._update_pen_property(model_id, prop, value)
        except Exception as e:
            logger.error(f"Error updating trace {model_id}.{prop}: {e}")

    def _fast_update_data(self, trace_id: str, data_tuple: tuple) -> None:
        trace_model, curve = self.traces[trace_id]
        x_data, y_data = data_tuple

        if not isinstance(x_data, np.ndarray):
            x_data = np.asarray(x_data)
        if not isinstance(y_data, np.ndarray):
            y_data = np.asarray(y_data)

        curve.setData(x_data, y_data, connect='finite')

        if trace_id in self.isolated_view_boxes and y_data.size > 0:
            self._fast_update_isolated_range(trace_id, y_data)

    def _update_color(self, trace_id: str, color: str) -> None:
        trace_model, curve = self.traces[trace_id]
        pen = curve.opts['pen']
        pen.setColor(pg.mkColor(color))
        curve.setPen(pen)
        
        if trace_id in self.isolated_axes:
            self.isolated_axes[trace_id].setPen(pg.mkPen(color))

    def _update_visibility(self, trace_id: str, visible: bool) -> None:
        trace_model, curve = self.traces[trace_id]
        curve.setVisible(visible)
        
        if trace_id in self.isolated_axes:
            self.isolated_axes[trace_id].setVisible(visible)

    def _update_pen_property(self, trace_id: str, prop: str, value: Any) -> None:
        trace_model, curve = self.traces[trace_id]
        pen = curve.opts['pen']
        
        if prop == "width":
            pen.setWidth(value)
        elif prop == "style":
            pen.setStyle(self._get_qt_line_style(value))
            
        curve.setPen(pen)

    def _setup_isolated_view(self, trace_id: str, curve: pg.PlotDataItem, model) -> None:
        """Setup isolated view for a trace."""
        try:
            # Create axis
            color = model.get_property('color', '#ffffff')
            axis = pg.AxisItem("right", pen=pg.mkPen(color))
            
            # Add to layout
            next_col = len(self.isolated_axes) + 1
            self.plot_layout.addItem(axis, row=0, col=next_col)
            self.isolated_axes[trace_id] = axis

            # Create and link view box
            view_box = pg.ViewBox()
            axis.linkToView(view_box)
            view_box.setXLink(self.plot_item.vb)
            
            # Add to scene
            self.plot_layout.scene().addItem(view_box)
            view_box.setGeometry(self.plot_item.vb.sceneBoundingRect())
            self.isolated_view_boxes[trace_id] = view_box
            
            # Add curve
            view_box.addItem(curve)

            # Set initial range if data exists
            y_data = model.y_data
            if y_data.size > 0:
                self._fast_update_isolated_range(trace_id, y_data)

        except Exception as e:
            logger.error(f"Error setting up isolated view for {trace_id}: {e}")
            raise

    def remove_trace(self, trace_id: str) -> None:
        """Remove a trace and clean up resources."""
        if trace_id not in self.traces:
            return

        try:
            curve = self.traces[trace_id]
            
            # Remove from main plot if present
            if curve.scene() == self.plot_item.scene():
                self.plot_item.removeItem(curve)
            
            # Clean up isolated view
            if trace_id in self.isolated_view_boxes:
                viewbox = self.isolated_view_boxes[trace_id]
                viewbox.removeItem(curve)
                self.plot_layout.removeItem(viewbox)
                del self.isolated_view_boxes[trace_id]
                
            if trace_id in self.isolated_axes:
                self.plot_layout.removeItem(self.isolated_axes[trace_id])
                del self.isolated_axes[trace_id]
            
            # Remove curve
            del self.traces[trace_id]
            
        except Exception as e:
            logger.error(f"Error removing trace {trace_id}: {e}")

    def clear_all(self) -> None:
        """Remove all traces."""
        for trace_id in list(self.traces.keys()):
            self.remove_trace(trace_id)

    def update_geometry(self, rect) -> None:
        """Update view box geometries."""
        for view_box in self.isolated_view_boxes.values():
            view_box.setGeometry(rect)

    @staticmethod
    def _get_qt_line_style(style_str: str) -> Qt.PenStyle:
        """Convert string style to Qt PenStyle, normalizing the input."""
        normalized = style_str.lower().replace(" ", "").replace("-", "")
        styles = {
            "solid": Qt.SolidLine,
            "dash": Qt.DashLine,
            "dot": Qt.DotLine,
            "dashdot": Qt.DashDotLine
        }
        result = styles.get(normalized, Qt.SolidLine)
        logger.debug(f"_get_qt_line_style: converting '{style_str}' -> '{normalized}' -> {result}")
        return result
