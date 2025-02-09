from typing import Dict, Optional, Any
from PySide6.QtWidgets import QVBoxLayout, QSplitter, QSizePolicy
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QTransform
import pyqtgraph as pg
import numpy as np

from pymetr.views.widgets.base import BaseWidget
from pymetr.core.logging import logger
from pymetr.models import Plot, Trace

class PlotView(BaseWidget):
    """
    Thread-safe plot visualization with support for:
    - Multiple traces with independent axes
    - Region selection
    - Auto-ranging
    - Line styles and markers
    """
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, parent)
        
        # Storage for plot components
        self.traces: Dict[str, pg.PlotDataItem] = {}
        self.trace_view_boxes: Dict[str, pg.ViewBox] = {}
        self.trace_axes: Dict[str, pg.AxisItem] = {}
        self.additional_axes = []
        self.additional_view_boxes = []
        
        # Performance optimization: Add update flags
        self._roi_update_needed = False
        self._geometry_update_needed = False
        self._suppress_roi_updates = False
        
        # Range update debouncing
        self.range_update_timer = QTimer(self)
        self.range_update_timer.setSingleShot(True)
        self.range_update_timer.timeout.connect(self._apply_range_update)
        
        # Geometry update debouncing
        self.geometry_update_timer = QTimer(self)
        self.geometry_update_timer.setSingleShot(True)
        self.geometry_update_timer.timeout.connect(self._update_view_boxes)
        
        # ROI update debouncing
        self.roi_update_timer = QTimer(self)
        self.roi_update_timer.setSingleShot(True)
        self.roi_update_timer.timeout.connect(self._apply_roi_update)
        
        # Set up UI
        self._setup_ui()
        
        # Set model and connect signals
        self.set_model(model_id)

    def set_model(self, model_id: str):
        """Set the plot model and establish connections."""
        super().set_model(model_id)
        if self.model:
            # Initial setup
            self._update_plot_title(self.model.get_property("title", "Untitled Plot"))
            self._update_plot_settings()
            
            # Connect to state signals for this plot's children
            self.state.models_linked.connect(self._handle_models_linked)
            self.state.model_changed.connect(self._handle_model_changed)
            
            # Add existing traces
            for trace in self.model.get_traces():
                self._add_trace(trace)

    def _setup_ui(self):
        """Initialize plot UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Main plot container
        self.plot_container = QSplitter(Qt.Vertical)
        layout.addWidget(self.plot_container)
        
        # Create plot layout
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_layout.setBackground('#1E1E1E')
        self.plot_container.addWidget(self.plot_layout)
        
        # Main plot with axis items
        self.plot_item = self.plot_layout.addPlot(row=0, col=0)
        self._setup_plot_area(self.plot_item, is_roi=False)
        
        # Add title label with proper styling
        self.plot_item.setTitle(title="", size="20pt", color='w')
        
        # ROI plot area
        self.roi_plot_area = pg.PlotWidget()
        self.roi_plot_area.setMinimumHeight(60)
        self.roi_plot_area.setMaximumHeight(60)
        self.roi_plot_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.roi_plot_area.setBackground('#2A2A2A')
        
        self.roi_plot_item = self._setup_plot_area(self.roi_plot_area.getPlotItem(), is_roi=True)
        self.plot_container.addWidget(self.roi_plot_area)
        
        # ROI region selector
        self.roi = pg.LinearRegionItem()
        self.roi_plot_item.addItem(self.roi)
        self.roi.sigRegionChanged.connect(self._handle_roi_changed)
        
        # Set initial splitter sizes
        self.plot_container.setSizes([600, 100])
        
        # Register mouse handlers
        self.plot_item.scene().sigMouseClicked.connect(self._handle_mouse_clicked)
        self.plot_item.sigRangeChanged.connect(self._handle_main_plot_range_changed)

    def _setup_plot_area(self, plot_item: pg.PlotItem, is_roi: bool = False) -> pg.PlotItem:
        """Configure plot area with proper styling."""
        plot_item.showGrid(x=True, y=True, alpha=0.3)
        
        # White axes and labels
        for axis in [plot_item.getAxis('left'), plot_item.getAxis('bottom')]:
            axis.setPen(pg.mkPen('w'))
            axis.setTextPen(pg.mkPen('w'))
            axis.setStyle(tickTextOffset=5, tickLength=-10)
            
        if is_roi:
            plot_item.getAxis('left').hide()
            plot_item.showGrid(x=True, y=False)
            plot_item.setMouseEnabled(x=False, y=False)
            
        return plot_item

    def _update_plot_title(self, title: str):
        """Update the plot title with proper styling."""
        if hasattr(self, 'plot_item'):
            self.plot_item.setTitle(title=title, size="20pt", color='w')

    def _update_plot_settings(self):
        """Update plot settings from model properties."""
        if not self.model:
            return
            
        # Grid
        grid_enabled = self.model.get_property("grid_enabled", True)
        self.plot_item.showGrid(x=grid_enabled, y=grid_enabled)
        
        # Axes labels
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
        
        # ROI visibility
        roi_visible = self.model.get_property("roi_visible", True)
        self.roi_plot_area.setVisible(roi_visible)
        
        # Initial ROI position
        roi = self.model.get_property("roi", None)
        if roi and len(roi) == 2:
            self.roi.setRegion(roi)

    def _handle_models_linked(self, parent_id: str, child_id: str):
        """Handle new model relationships."""
        if not self.model or parent_id != self.model.id:
            return
            
        child = self.state.get_model(child_id)
        if isinstance(child, Trace):
            self._add_trace(child)

    @Slot(str, str, object)
    def _handle_model_changed(self, model_id: str, prop: str, value: Any):
        """Handle model property changes."""
        if not self.model:
            return
            
        # Plot property changes
        if model_id == self.model.id:
            if prop == "title":
                self._update_plot_title(value)
            elif prop in ["grid_enabled", "x_label", "y_label", "x_unit", "y_unit", "roi_visible"]:
                self._update_plot_settings()
                
        # Trace property changes
        elif model_id in self.traces:
            self._handle_trace_property_changed(model_id, prop, value)

    def _handle_trace_property_changed(self, trace_id: str, prop: str, value: Any):
        """Handle trace property changes efficiently."""
        if trace_id not in self.traces:
            return
            
        curve = self.traces[trace_id]
        if prop == "data":
            self._update_trace_data(trace_id, value)
        elif prop == "visible":
            curve.setVisible(value)
            self._roi_update_needed = True
            self.roi_update_timer.start(100)
        elif prop == "color":
            self._update_trace_color(trace_id, value)
        elif prop == "style":
            self._update_trace_style(trace_id, value)
        elif prop == "width":
            self._update_trace_width(trace_id, value)
        elif prop == "mode":
            self._update_trace_mode(trace_id, value)

    def _update_trace_data(self, trace_id: str, data: tuple):
        """Update trace data efficiently."""
        if trace_id not in self.traces:
            return
            
        curve = self.traces[trace_id]
        x_data, y_data = data
        
        # Update curve data without recreating the curve
        curve.setData(x_data, y_data, connect='finite')
        
        # Queue ROI update
        self._roi_update_needed = True
        self.roi_update_timer.start(100)
        
        # Auto-range based on all visible traces
        x_ranges = []
        y_ranges = []
        for t_id, curve in self.traces.items():
            if curve.isVisible():
                data = curve.getData()
                if data[0].size > 0:
                    x_ranges.extend([np.nanmin(data[0]), np.nanmax(data[0])])
                    y_ranges.extend([np.nanmin(data[1]), np.nanmax(data[1])])
        
        if x_ranges and y_ranges:
            x_min, x_max = min(x_ranges), max(x_ranges)
            y_min, y_max = min(y_ranges), max(y_ranges)
            
            if all(np.isfinite([x_min, x_max, y_min, y_max])):
                x_padding = (x_max - x_min) * 0.05
                y_padding = (y_max - y_min) * 0.05
                
                self._suppress_roi_updates = True
                self.plot_item.setXRange(x_min - x_padding, x_max + x_padding)
                self.plot_item.setYRange(y_min - y_padding, y_max + y_padding)
                self._suppress_roi_updates = False

        # Handle auto-range for isolated traces
        if trace_id in self.trace_view_boxes:
            viewbox = self.trace_view_boxes[trace_id]
            if len(y_data) > 0:
                ymin, ymax = np.nanmin(y_data), np.nanmax(y_data)
                if np.isfinite(ymin) and np.isfinite(ymax):
                    padding = (ymax - ymin) * 0.1
                    viewbox.setYRange(ymin - padding, ymax + padding)

    def _update_trace_color(self, trace_id: str, color: str):
        """Update trace color efficiently."""
        if trace_id not in self.traces:
            return
            
        curve = self.traces[trace_id]
        pen = curve.opts['pen']
        pen.setColor(pg.mkColor(color))
        curve.setPen(pen)
        
        # Update axis color if isolated
        if trace_id in self.trace_axes:
            self.trace_axes[trace_id].setPen(pg.mkPen(color=color))

    def _update_trace_style(self, trace_id: str, style: str):
        """Update trace line style."""
        if trace_id not in self.traces:
            return
            
        curve = self.traces[trace_id]
        pen = curve.opts['pen']
        pen.setStyle(self._get_qt_line_style(style))
        curve.setPen(pen)

    def _update_trace_width(self, trace_id: str, width: int):
        """Update trace line width."""
        if trace_id not in self.traces:
            return
            
        curve = self.traces[trace_id]
        pen = curve.opts['pen']
        pen.setWidth(width)
        curve.setPen(pen)

    def _update_trace_mode(self, trace_id: str, mode: str):
        """Handle trace mode changes (Group/Isolate)."""
        if trace_id not in self.traces:
            return
            
        curve = self.traces[trace_id]
        trace_model = self.state.get_model(trace_id)
        if not trace_model:
            return
            
        if mode == "Isolate" and trace_id not in self.trace_view_boxes:
            # Remove from main plot
            self.plot_item.removeItem(curve)
            self._setup_isolated_trace(trace_model, curve)
            
        elif mode == "Group" and trace_id in self.trace_view_boxes:
            # Remove from isolated view
            viewbox = self.trace_view_boxes[trace_id]
            axis = self.trace_axes[trace_id]
            
            viewbox.removeItem(curve)
            
            # Clean up axis and viewbox
            if axis in self.additional_axes:
                self.additional_axes.remove(axis)
            if viewbox in self.additional_view_boxes:
                self.additional_view_boxes.remove(viewbox)
                
            self.plot_layout.removeItem(axis)
            axis.deleteLater()
            
            self.plot_layout.scene().removeItem(viewbox)
            viewbox.deleteLater()
            
            del self.trace_view_boxes[trace_id]
            del self.trace_axes[trace_id]
            
            # Add back to main plot
            self.plot_item.addItem(curve)
            
        self._queue_geometry_update()

    def _add_trace(self, trace_model):
        """Add a single trace to the plot with proper styling."""
        if trace_model.id in self.traces:
            return
            
        # Create pen with initial style
        pen = pg.mkPen(
            color=trace_model.get_property('color', '#ffffff'),
            width=trace_model.get_property('width', 1),
            style=self._get_qt_line_style(trace_model.get_property('style', 'solid'))
        )
        
        # Create curve with efficient data handling
        curve = pg.PlotDataItem(
            trace_model.x_data,
            trace_model.y_data,
            pen=pen,
            name=trace_model.get_property('name', ''),
            connect='finite'  # Efficient line drawing
        )
        
        self.traces[trace_model.id] = curve
        
        # Handle isolated vs grouped traces
        if trace_model.get_property('mode') == "Isolate":
            self._setup_isolated_trace(trace_model, curve)
        else:
            self.plot_item.addItem(curve)
            
        curve.setVisible(trace_model.get_property('visible', True))

    def _setup_isolated_trace(self, trace_model, curve):
        """Setup isolated trace with its own axis and viewbox."""
        # Create axis with trace color
        color = trace_model.get_property('color', '#ffffff')
        pen = pg.mkPen(color=color)
        axis = pg.AxisItem("right", pen=pen)
        
        # Calculate position for new axis
        next_col = len(self.additional_axes) + 1
        self.plot_layout.addItem(axis, row=0, col=next_col)
        self.additional_axes.append(axis)
        self.trace_axes[trace_model.id] = axis
        
        # Create and link viewbox
        view_box = pg.ViewBox()
        axis.linkToView(view_box)
        view_box.setXLink(self.plot_item.vb)
        self.plot_layout.scene().addItem(view_box)
        
        # Set initial geometry
        view_box.setGeometry(self.plot_item.vb.sceneBoundingRect())
        self.additional_view_boxes.append(view_box)
        self.trace_view_boxes[trace_model.id] = view_box
        
        view_box.addItem(curve)
        
        # Set initial range if data exists
        if len(trace_model.y_data) > 0:
            ymin, ymax = np.nanmin(trace_model.y_data), np.nanmax(trace_model.y_data)
            if np.isfinite(ymin) and np.isfinite(ymax):
                padding = (ymax - ymin) * 0.1
                view_box.setYRange(ymin - padding, ymax + padding)

    @Slot(object)
    def _handle_mouse_clicked(self, event):
        """Handle mouse clicks for plot interaction."""
        if event.double():
            scene_point = event.scenePos()
            transform = QTransform()
            clicked_item = self.plot_item.scene().itemAt(scene_point, transform)
            
            # Check if clicked on an isolated axis
            for trace_id, axis in self.trace_axes.items():
                if axis.boundingRect().contains(axis.mapFromScene(scene_point)):
                    if trace_id in self.trace_view_boxes:
                        self._suppress_roi_updates = True
                        self.trace_view_boxes[trace_id].autoRange(padding=0.1)
                        self._suppress_roi_updates = False
                    return
                    
            # If not on an axis, autoscale main plot
            self._suppress_roi_updates = True
            self.plot_item.autoRange(padding=0.1)
            self._suppress_roi_updates = False

    def _handle_roi_changed(self):
        """Handle ROI region changes with update suppression."""
        if not self.model or self._suppress_roi_updates:
            return
            
        region = self.roi.getRegion()
        region_list = [float(x) for x in region]
        
        if region_list != self.model.get_property('roi'):
            self.model.set_property('roi', region_list)
            self._suppress_roi_updates = True
            self.plot_item.setXRange(*region, padding=0)
            self._suppress_roi_updates = False

    @Slot(object, object)
    def _handle_main_plot_range_changed(self, viewbox, ranges):
        """Update ROI when main plot range changes."""
        if self._suppress_roi_updates:
            return
            
        self.latest_x_range = ranges[0]
        self.range_update_timer.start(200)  # Debounce rapid updates
        
        if self.roi:
            self.roi.setRegion(ranges[0])

    def _handle_trace_data_changed(self, trace_id: str):
        """Handle trace data updates efficiently."""
        if trace_id not in self.traces:
            return
            
        curve = self.traces[trace_id]
        trace_model = self.model.children[trace_id]
        
        # Update curve data without recreating the curve
        curve.setData(trace_model.x_data, trace_model.y_data, connect='finite')
        
        # Auto-range based on all visible traces
        x_ranges = []
        y_ranges = []
        for t_id, curve in self.traces.items():
            if curve.isVisible():
                data = curve.getData()
                if data[0].size > 0:
                    x_ranges.extend([np.nanmin(data[0]), np.nanmax(data[0])])
                    y_ranges.extend([np.nanmin(data[1]), np.nanmax(data[1])])
        
        if x_ranges and y_ranges:
            x_min, x_max = min(x_ranges), max(x_ranges)
            y_min, y_max = min(y_ranges), max(y_ranges)
            
            if all(np.isfinite([x_min, x_max, y_min, y_max])):
                x_padding = (x_max - x_min) * 0.05
                y_padding = (y_max - y_min) * 0.05
                
                self._suppress_roi_updates = True
                self.plot_item.setXRange(x_min - x_padding, x_max + x_padding)
                self.plot_item.setYRange(y_min - y_padding, y_max + y_padding)
                self._suppress_roi_updates = False
        
        # Handle auto-range for isolated traces
        if trace_id in self.trace_view_boxes:
            viewbox = self.trace_view_boxes[trace_id]
            if len(trace_model.y_data) > 0:
                ymin, ymax = np.nanmin(trace_model.y_data), np.nanmax(trace_model.y_data)
                if np.isfinite(ymin) and np.isfinite(ymax):
                    padding = (ymax - ymin) * 0.1
                    viewbox.setYRange(ymin - padding, ymax + padding)
                    
        # Queue ROI update
        self._roi_update_needed = True
        self.roi_update_timer.start(100)

    @Slot()
    def _apply_range_update(self):
        """Apply the queued range update to the model."""
        if self.model and hasattr(self, 'latest_x_range'):
            self.model.set_property('x_lim', list(self.latest_x_range))
            self.model.set_property('roi', list(self.latest_x_range))

    @Slot()
    def _apply_roi_update(self):
        """Apply queued ROI updates."""
        if not self._roi_update_needed:
            return
            
        self.roi_plot_area.clear()
        
        if not self.model:
            return
            
        # Calculate full data range efficiently
        x_ranges = []
        for trace_id, curve in self.traces.items():
            if curve.isVisible():
                data = curve.getData()
                if data[0].size > 0:
                    x_ranges.append((np.nanmin(data[0]), np.nanmax(data[0])))
                    
        if x_ranges:
            x_min = min(r[0] for r in x_ranges)
            x_max = max(r[1] for r in x_ranges)
            if np.isfinite(x_min) and np.isfinite(x_max):
                padding = (x_max - x_min) * 0.05
                self.roi_plot_item.setXRange(x_min - padding, x_max + padding, padding=0)
            
        # Add visible traces to ROI plot efficiently
        for trace_id, curve in self.traces.items():
            if curve.isVisible():
                data = curve.getData()
                # Use the same pen settings for consistency
                self.roi_plot_area.plot(data[0], data[1], pen=curve.opts['pen'])
                
        # Re-add ROI
        self.roi_plot_area.addItem(self.roi)
        self._roi_update_needed = False

    def _update_view_boxes(self):
        """Update all isolated viewbox geometries."""
        if not self._geometry_update_needed:
            return
            
        main_rect = self.plot_item.vb.sceneBoundingRect()
        for view_box in self.additional_view_boxes:
            view_box.setGeometry(main_rect)
            view_box.linkedViewChanged(self.plot_item.vb, view_box.XAxis)
            
        self._geometry_update_needed = False

    def _queue_geometry_update(self):
        """Queue a geometry update with debouncing."""
        self._geometry_update_needed = True
        self.geometry_update_timer.start(100)  # 100ms debounce

    def resizeEvent(self, event):
        """Handle widget resize events."""
        super().resizeEvent(event)
        self._queue_geometry_update()

    def showEvent(self, event):
        """Handle widget show events."""
        super().showEvent(event)
        self._queue_geometry_update()

    @staticmethod
    def _get_qt_line_style(style_str: str) -> Qt.PenStyle:
        """Convert style string to Qt pen style."""
        return {
            'solid': Qt.SolidLine,
            'dash': Qt.DashLine,
            'dot': Qt.DotLine,
            'dash-dot': Qt.DashDotLine
        }.get(style_str.lower(), Qt.SolidLine)

    def clear(self):
        """Clear all plot items with proper cleanup."""
        # Disconnect from state signals
        self.state.models_linked.disconnect(self._handle_models_linked)
        self.state.model_changed.disconnect(self._handle_model_changed)
        
        # Clear main plot traces
        for curve in self.traces.values():
            if curve.parentItem() == self.plot_item:
                self.plot_item.removeItem(curve)
                
        # Clear isolated viewboxes and axes
        for trace_id in list(self.trace_view_boxes.keys()):
            if trace_id in self.trace_axes:
                axis = self.trace_axes[trace_id]
                self.plot_layout.removeItem(axis)
                self.additional_axes.remove(axis)
                axis.deleteLater()
                
            viewbox = self.trace_view_boxes[trace_id]
            self.plot_layout.scene().removeItem(viewbox)
            self.additional_view_boxes.remove(viewbox)
            viewbox.deleteLater()
            
        # Clear storage
        self.traces.clear()
        self.trace_view_boxes.clear()
        self.trace_axes.clear()
        self.additional_axes.clear()
        self.additional_view_boxes.clear()

    def closeEvent(self, event):
        """Clean up resources when widget is closed."""
        self.clear()
        super().closeEvent(event)