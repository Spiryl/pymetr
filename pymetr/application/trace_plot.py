import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt

from pymetr.instrument import Trace

class TracePlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_item = self.plot_layout.addPlot(row=0, col=0)
        self.plot_item.showGrid(x=True, y=True)
        self.legend = pg.LegendItem(offset=(70, 30))
        self.legend.setParentItem(self.plot_item)

        self.additional_axes = []
        self.additional_view_boxes = []
        self.trace_view_boxes = {}
        self.trace_axes = {}
        self.traces = []

        self.roi_plot_item = None
        self.roi_plot = None
        self.roi = None

        self.plot_item.vb.sigRangeChanged.connect(self.on_main_plot_range_changed)

        layout = QVBoxLayout(self)
        layout.addWidget(self.plot_layout)

    def on_roi_plot_enabled(self, enabled):
        if enabled:
            self.roi_plot_item = self.plot_layout.addPlot(row=1, col=0)
            self.roi_plot_item.setMaximumHeight(100)
            self.roi_plot = self.roi_plot_item.vb

            self.roi = pg.LinearRegionItem()
            self.roi.setZValue(-10)
            self.roi_plot.addItem(self.roi)

            self.roi.sigRegionChanged.connect(self.update_main_plot)
            self.plot_item.sigXRangeChanged.connect(self.update_roi_plot)

            self.update_roi_plot()
            self.autoscale_roi_plot()
            self.set_roi_region()
        else:
            if self.roi_plot_item is not None:
                self.plot_layout.removeItem(self.roi_plot_item)
                self.roi_plot_item = None
                self.roi_plot = None
                self.roi = None

    def on_main_plot_range_changed(self, view_box, range_):
        if self.roi is not None:
            self.roi.setRegion(view_box.viewRange()[0])

    def clear_roi_plot(self):
        if self.roi_plot_item is not None:
            self.roi_plot_item.clear()

    def update_main_plot(self):
        if self.roi is not None:
            self.plot_item.vb.setXRange(*self.roi.getRegion(), padding=0)

    def autoscale_roi_plot(self):
        if self.roi_plot_item is not None:
            self.roi_plot_item.enableAutoRange()

    def set_roi_region(self):
        if self.roi is not None:
            self.roi.setRegion(self.plot_item.vb.viewRange()[0])

    def update_plot(self, trace_data):
        print(f"Received trace data in TracePlot: {trace_data}")
        self.trace_data = trace_data
        self.plot_item.clear()
        self.clear_traces()
        if self.roi_plot_item is not None:
            self.roi_plot_item.clear()

        for trace in trace_data:
            self.create_or_update_trace(trace.label, trace.__dict__)

        self.plot_item.vb.sigResized.connect(self.update_view_boxes)
        self.restore_view_ranges(trace_data)
        self.update_roi_plot()
        self.update_view_boxes()

    def create_or_update_trace(self, trace_label, trace_attrs):
        # Similar to existing logic but refactored into a separate method for clarity
        visible = trace_attrs.get('visible', True)
        if visible:
            pen = pg.mkPen(color=trace_attrs.get('color', 'ffffff'), width=trace_attrs.get('line_thickness', 1.0), style=self.get_line_style(trace_attrs.get('line_style', 'Solid')))
            x = trace_attrs.get('x_data', np.arange(len(trace_attrs['data'])))
            y = trace_attrs['data']
            if trace_attrs.get('mode', 'Group') == "Group":
                curve = pg.PlotCurveItem(x, y, pen=pen, name=trace_label)
                self.plot_item.addItem(curve)
                self.legend.addItem(curve, trace_label)
            else:  # Isolate mode
                self.handle_isolated_trace(trace_label, x, y, pen, trace_attrs)

    def update_roi_plot(self):
        if self.roi_plot_item is not None:
            # Clear existing curves in ROI plot item without removing the plot item itself
            self.roi_plot_item.clearPlots()

            # Redraw only the visible traces in the ROI plot
            for trace_label, trace_attrs in self.trace_data.items():  # Assuming trace_data is kept up-to-date
                if trace_attrs['visible']:
                    x = trace_attrs.get('x_data', np.arange(len(trace_attrs['data'])))
                    y = trace_attrs['data']
                    pen = pg.mkPen(color=trace_attrs['color'], width=trace_attrs['line_thickness'], style=self.get_line_style(trace_attrs['line_style']))
                    self.roi_plot_item.plot(x, y, pen=pen, name=trace_attrs['label'])

            # Automatically adjust the range to fit all visible traces
            self.roi_plot_item.autoRange()

    def handle_isolated_trace(self, trace_label, x, y, pen, trace_attrs):
        """Handle creation or update of isolated traces with dedicated axes."""
        if trace_label in self.trace_view_boxes:
            view_box = self.trace_view_boxes[trace_label]
            axis = self.trace_axes[trace_label]
        else:
            # Create new axis and view box for the isolated trace
            axis = pg.AxisItem("right", pen=pen)
            self.plot_layout.addItem(axis, row=0, col=1 + len(self.additional_axes))
            self.additional_axes.append(axis)

            view_box = pg.ViewBox()
            axis.linkToView(view_box)
            view_box.setXLink(self.plot_item.vb)
            self.plot_layout.scene().addItem(view_box)
            self.additional_view_boxes.append(view_box)

            self.trace_view_boxes[trace_label] = view_box
            self.trace_axes[trace_label] = axis

        # Add or update the curve in the view box
        curve = pg.PlotCurveItem(x, y, pen=pen, name=trace_label)
        view_box.addItem(curve)
        self.legend.addItem(curve, trace_label)
        self.traces.append(curve)

        # Set the Y-range if it's specified in trace attributes
        if 'y_range' in trace_attrs:
            view_box.setRange(yRange=trace_attrs['y_range'])
            view_box.enableAutoRange(axis='y', enable=False)
            
    def clear_traces(self):
        for trace in self.traces:
            if hasattr(trace, 'getViewBox') and trace.getViewBox():
                trace.getViewBox().removeItem(trace)
            else:
                self.plot_item.removeItem(trace)
        self.traces = []
        self.legend.clear()

        # Clear additional axes that are no longer needed
        for axis in self.additional_axes:
            self.plot_layout.removeItem(axis)
            axis.deleteLater()
        self.additional_axes.clear()

    def restore_view_ranges(self, trace_data):
        if self.plot_item.vb.viewRange()[0] is not None:
            self.plot_item.vb.setRange(xRange=self.plot_item.vb.viewRange()[0], yRange=self.plot_item.vb.viewRange()[1], padding=0)
        for trace in trace_data:
            if trace.mode == "Isolate" and trace.y_range is not None:
                view_box = self.trace_view_boxes.get(trace.label)
                if view_box:
                    view_box.setRange(yRange=trace.y_range, padding=0)

    def get_line_style(self, line_style):
        if line_style == 'Solid':
            return Qt.SolidLine
        elif line_style == 'Dash':
            return Qt.DashLine
        elif line_style == 'Dot':
            return Qt.DotLine
        elif line_style == 'Dash-Dot':
            return Qt.DashDotLine
        else:
            return Qt.SolidLine

    def handle_view_box_range_changed(self, view_box, trace):
        x_range, y_range = view_box.viewRange()
        if isinstance(trace, list):
            for t in trace:
                if isinstance(t, Trace):
                    t.x_range = x_range
                    t.y_range = y_range
                    print(f"Trace: {t.label}, X-Range: {x_range}, Y-Range: {y_range}")
                else:
                    print(f"Unexpected element in trace list: {t}")
        elif isinstance(trace, Trace):
            trace.x_range = x_range
            trace.y_range = y_range
            print(f"Trace: {trace.label}, X-Range: {x_range}, Y-Range: {y_range}")
        else:
            print(f"Unexpected trace object: {trace}")

    def clear_additional_axes(self):
        for axis in self.additional_axes:
            self.plot_layout.removeItem(axis)
            axis.deleteLater()
        for view_box in self.additional_view_boxes:
            self.plot_layout.scene().removeItem(view_box)
            view_box.deleteLater()
        self.additional_axes.clear()
        self.additional_view_boxes.clear()
        self.legend.clear()
        self.trace_view_boxes.clear()
        self.trace_axes.clear()

    def update_view_boxes(self):
        for view_box in self.additional_view_boxes:
            view_box.setGeometry(self.plot_item.vb.sceneBoundingRect())