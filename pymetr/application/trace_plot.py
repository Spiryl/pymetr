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
        self.traces = {}  # Storing Trace objects
        self.trace_curves = {}  # Storing PlotCurveItem references

        self.init_roi_plot()
        layout = QVBoxLayout(self)
        layout.addWidget(self.plot_layout)

    def init_roi_plot(self):
        self.roi_plot_item = self.plot_layout.addPlot(row=1, col=0)
        self.roi_plot_item.setMaximumHeight(100)
        self.roi_plot_item.hide()  # Start as hidden
        self.roi = pg.LinearRegionItem()
        self.roi.setZValue(10)
        self.roi_plot = self.roi_plot_item.vb  # Properly assign the viewbox of the ROI plot item
        self.roi_plot.addItem(self.roi)  # Add the LinearRegionItem to the correct viewbox
        self.roi.sigRegionChanged.connect(self.update_main_plot)
        self.plot_item.sigXRangeChanged.connect(self.on_main_plot_range_changed)

    def on_roi_plot_enabled(self, enabled):
        if self.roi_plot_item is not None:
            self.roi_plot_item.setVisible(enabled)  # Toggle visibility
            if enabled:
                self.update_roi_plot(self.traces)  # Ensure this uses current traces
                self.set_roi_region()  # Adjust the ROI to current range

    def update_roi_plot(self, traces):
        if self.roi_plot_item is None or not self.roi_plot_item.isVisible():
            return

        self.roi_plot_item.clear()
        for trace in traces:
            if trace.visible:
                x_data = trace.x_data if trace.x_data is not None else np.arange(len(trace.data))
                self.roi_plot_item.plot(x_data, trace.data, pen=pg.mkPen(trace.color, width=trace.line_thickness))
        
        self.autoscale_roi_plot()

    def set_roi_region(self):
        if self.roi is not None and self.plot_item is not None:
            current_range = self.plot_item.viewRange()[0]
            self.roi.setRegion(current_range)

    def autoscale_roi_plot(self):
        if self.roi_plot_item is not None:
            self.roi_plot.enableAutoRange()

    def on_main_plot_range_changed(self, view_box, range_):
        if self.roi is not None:
            self.roi.setRegion(view_box.viewRange()[0])

    def clear_roi_plot(self):
        if self.roi_plot_item is not None:
            self.roi_plot_item.clear()

    def update_main_plot(self):
        if self.roi is not None:
            self.plot_item.vb.setXRange(*self.roi.getRegion(), padding=0)

    def update_plot(self, trace_data):
        print(f"Received trace data in TracePlot: {trace_data}")
        self.plot_item.clear()
        self.clear_additional_axes()

        for trace in trace_data:
            visible = trace.visible
            color = trace.color
            legend_alias = trace.label
            x = trace.x_data if trace.x_data is not None else np.arange(len(trace.data))
            y = trace.data
            mode = trace.mode

            if visible:
                pen = pg.mkPen(color=color, width=trace.line_thickness, style=self.get_line_style(trace.line_style))

                if mode == "Group":
                    curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                    self.plot_item.addItem(curve)
                    self.legend.addItem(curve, legend_alias)
                    self.trace_curves[trace.label] = curve
                else:  # Isolate mode
                    if trace.label in self.trace_view_boxes:
                        view_box = self.trace_view_boxes[trace.label]
                        axis = self.trace_axes[trace.label]
                    else:
                        axis = pg.AxisItem("right", pen=pen)
                        self.plot_layout.addItem(axis, row=0, col=len(self.additional_axes) + 1)
                        self.additional_axes.append(axis)

                        view_box = pg.ViewBox()
                        axis.linkToView(view_box)
                        view_box.setXLink(self.plot_item.vb)
                        self.plot_layout.scene().addItem(view_box)
                        self.additional_view_boxes.append(view_box)

                        self.trace_view_boxes[trace.label] = view_box
                        self.trace_axes[trace.label] = axis

                    curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                    view_box.addItem(curve)
                    self.legend.addItem(curve, legend_alias)
                    self.trace_curves[trace.label] = curve

                    if trace.y_range is not None:
                        view_box.setRange(yRange=trace.y_range)
                        view_box.enableAutoRange(axis='y', enable=False)
                    else:
                        view_box.setRange(yRange=self.plot_item.vb.viewRange()[1])

        self.plot_item.vb.sigResized.connect(self.update_view_boxes)  # Connect the sigResized signal
        self.update_view_boxes()  # Update the position and size of the view boxes initially
        self.restore_view_ranges(trace_data)
        self.update_roi_plot(trace_data)

    def clear_traces(self):
        for curve in self.trace_curves.values():
            if curve.getViewBox():
                curve.getViewBox().removeItem(curve)
            else:
                self.plot_item.removeItem(curve)
        self.traces.clear()
        self.trace_curves.clear()
        self.legend.clear()

        # Clear additional axes
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