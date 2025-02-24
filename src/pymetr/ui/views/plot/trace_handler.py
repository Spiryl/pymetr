from PySide6.QtCore import QObject, Qt
import pyqtgraph as pg
import numpy as np
from typing import Dict, Any, Tuple
from pymetr.core.logging import logger

class TraceHandler(QObject):
    """
    High-performance trace handler optimized for real-time visualization.
    """
    
    def __init__(self, plot_item: pg.PlotItem, plot_layout: pg.GraphicsLayoutWidget):
        super().__init__()
        self.plot_item = plot_item
        self.plot_layout = plot_layout
        
        # Store tuple: (trace_model, curve)
        self.traces: Dict[str, Tuple[Any, pg.PlotDataItem]] = {}
        self.isolated_axes: Dict[str, pg.AxisItem] = {}
        self.isolated_view_boxes: Dict[str, pg.ViewBox] = {}
        
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

            # Store both model and curve
            self.traces[trace_id] = (trace_model, curve)
            
            # Handle isolation mode
            mode = trace_model.get_property('mode', 'Group')
            logger.debug(f"Adding trace {trace_id} in {mode} mode")
            
            if mode == "Isolate":
                self._setup_isolated_view(trace_id, curve, trace_model)
            else:
                self.plot_item.addItem(curve)

            # Set initial visibility
            curve.setVisible(trace_model.get_property('visible', True))

        except Exception as e:
            logger.error(f"Error adding trace {trace_id}: {e}")
            self.remove_trace(trace_id)

    def handle_property_change(self, model_id: str, model_type: str, prop: str, value: Any):
        """Handle trace property changes."""
        if model_id not in self.traces:
            return

        try:
            _, curve = self.traces[model_id]
            
            if prop == "data":
                x_data, y_data = value
                curve.setData(x_data, y_data, connect='finite')
                
            elif prop == "color":
                pen = curve.opts['pen']
                pen.setColor(pg.mkColor(value))
                curve.setPen(pen)
                if model_id in self.isolated_axes:
                    self.isolated_axes[model_id].setPen(pg.mkPen(value))
                    
            elif prop == "visible":
                curve.setVisible(value)
                if model_id in self.isolated_axes:
                    self.isolated_axes[model_id].setVisible(value)
                    
            elif prop == "width":
                pen = curve.opts['pen']
                pen.setWidth(value)
                curve.setPen(pen)
                
            elif prop == "style":
                pen = curve.opts['pen']
                pen.setStyle(self._get_qt_line_style(value))
                curve.setPen(pen)
                
            elif prop == "mode":
                # Remove from current location
                if curve.scene() == self.plot_item.scene():
                    self.plot_item.removeItem(curve)
                elif model_id in self.isolated_view_boxes:
                    self.isolated_view_boxes[model_id].removeItem(curve)
                    self.plot_layout.removeItem(self.isolated_view_boxes[model_id])
                    del self.isolated_view_boxes[model_id]
                    self.plot_layout.removeItem(self.isolated_axes[model_id])
                    del self.isolated_axes[model_id]
                
                # Add to new location
                if value == "Isolate":
                    model = self.traces[model_id][0]  # Get the model from stored tuple
                    self._setup_isolated_view(model_id, curve, model)
                else:
                    self.plot_item.addItem(curve)

        except Exception as e:
            logger.error(f"Error updating trace {model_id}: {e}")

    def _setup_isolated_view(self, trace_id: str, curve: pg.PlotDataItem, model) -> None:
        """Create an isolated view for a trace."""
        try:
            color = model.get_property('color', '#ffffff')
            axis = pg.AxisItem("right")
            axis.setPen(pg.mkPen(color))
            
            next_col = len(self.isolated_axes) + 1
            self.plot_layout.addItem(axis, row=0, col=next_col)
            self.isolated_axes[trace_id] = axis

            view_box = pg.ViewBox()
            axis.linkToView(view_box)
            view_box.setXLink(self.plot_item.vb)
            
            self.plot_layout.scene().addItem(view_box)
            view_box.setGeometry(self.plot_item.vb.sceneBoundingRect())
            self.isolated_view_boxes[trace_id] = view_box
            
            view_box.addItem(curve)

            # Set initial range if data exists
            y_data = model.y_data
            if y_data.size > 0:
                ymin, ymax = np.nanmin(y_data), np.nanmax(y_data)
                if np.isfinite(ymin) and np.isfinite(ymax):
                    padding = (ymax - ymin) * 0.1
                    view_box.setYRange(ymin - padding, ymax + padding)

        except Exception as e:
            logger.error(f"Error setting up isolated view for {trace_id}: {e}")

    def remove_trace(self, trace_id: str) -> None:
        """Remove a trace and clean up resources."""
        if trace_id not in self.traces:
            return

        try:
            _, curve = self.traces[trace_id]
            
            # Remove from main plot if present
            if curve.scene() == self.plot_item.scene():
                self.plot_item.removeItem(curve)
            
            # Clean up isolated view if exists
            if trace_id in self.isolated_view_boxes:
                viewbox = self.isolated_view_boxes[trace_id]
                viewbox.removeItem(curve)
                self.plot_layout.removeItem(viewbox)
                del self.isolated_view_boxes[trace_id]
                
            if trace_id in self.isolated_axes:
                self.plot_layout.removeItem(self.isolated_axes[trace_id])
                del self.isolated_axes[trace_id]
            
            # Remove from traces dictionary
            del self.traces[trace_id]
            
        except Exception as e:
            logger.error(f"Error removing trace {trace_id}: {e}")

    def clear_all(self) -> None:
        """Remove all traces."""
        for trace_id in list(self.traces.keys()):
            self.remove_trace(trace_id)

    @staticmethod
    def _get_qt_line_style(style_str: str) -> Qt.PenStyle:
        """Convert string style to Qt PenStyle."""
        styles = {
            'solid': Qt.SolidLine,
            'dash': Qt.DashLine,
            'dot': Qt.DotLine,
            'dashdot': Qt.DashDotLine
        }
        return styles.get(style_str.lower(), Qt.SolidLine)

    def update_geometry(self, main_rect) -> None:
        """Update geometry of isolated view boxes."""
        for view_box in self.isolated_view_boxes.values():
            view_box.setGeometry(main_rect)