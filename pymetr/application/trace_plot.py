# --- trace_plot.py ---
import sys
import pyqtgraph as pg
import pyqtgraph as pg
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QDockWidget, QComboBox
from PySide6.QtCore import QObject, Signal, Qt
import numpy as np

from pymetr.application.trace_dock import TraceManager, TraceDock

class TracePlot(QWidget):
    def __init__(self, trace_manager, parent=None):
        super().__init__(parent)
        self.trace_manager = trace_manager
        self.layout = QVBoxLayout(self)
        self.setup_main_plot()
        self.setup_roi_plot()
        self.traces = {}
        self.trace_axes = {}
        self.trace_view_boxes = {}

        # Connecting signals
        self.trace_manager.traceDataUpdated.connect(self.update_plot)

    def setup_main_plot(self):
        self.plot_widget = pg.PlotWidget()
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.setTitle("Main Plot")
        self.plot_item.showGrid(x=True, y=True)
        self.legend = pg.LegendItem(offset=(70, 30), parentItem=self.plot_item)
        self.layout.addWidget(self.plot_widget)

    def setup_roi_plot(self):
        self.roi_plot_widget = pg.PlotWidget()
        self.roi_plot_widget.setMaximumHeight(100)
        self.roi_plot_item = self.roi_plot_widget.getPlotItem()
        self.roi_plot_item.setTitle("Region Plot")
        self.layout.addWidget(self.roi_plot_widget)
        self.roi = pg.LinearRegionItem()
        self.roi.setZValue(10)
        self.plot_item.addItem(self.roi)
        self.roi.sigRegionChanged.connect(self.update_roi_plot)

    def update_plot(self):
        self.plot_item.clear()
        self.legend.clear()
        for trace in self.trace_manager.traces:
            if trace.visible:
                if trace.mode == "Group":
                    self.add_trace_to_main_plot(trace)
                else:
                    self.add_trace_to_isolated_view(trace)

    def add_or_update_trace(self, trace):
        if trace.mode == "Group":
            self.add_trace_to_main_plot(trace)
        else:
            self.add_trace_to_isolated_view(trace)

    def add_trace_to_main_plot(self, trace):
        if trace.label in self.traces:
            curve = self.traces[trace.label]
            curve.setData(trace.data)
        else:
            pen = pg.mkPen(color=trace.color, width=trace.line_thickness, style=self.get_line_style(trace.line_style))
            curve = pg.PlotCurveItem(trace.data, pen=pen, name=trace.label)
            self.plot_item.addItem(curve)
            self.legend.addItem(curve, trace.label)
            self.traces[trace.label] = curve

    def add_trace_to_isolated_view(self, trace):
        if trace.label not in self.trace_axes:
            axis = pg.AxisItem("right")
            self.plot_item.layout.addItem(axis, 2, len(self.trace_axes) + 1)
            view_box = pg.ViewBox()
            axis.linkToView(view_box)
            self.plot_item.scene().addItem(view_box)
            self.trace_axes[trace.label] = axis
            self.trace_view_boxes[trace.label] = view_box
        curve = pg.PlotCurveItem(trace.data, pen=pg.mkPen(color=trace.color))
        self.trace_view_boxes[trace.label].addItem(curve)
        self.traces[trace.label] = curve

    def update_roi_plot(self):
        # Handle updating ROI plot based on region changes in main plot
        region = self.roi.getRegion()
        self.roi_plot_item.setXRange(*region, padding=0)
        self.roi_plot_item.clear()
        for trace in self.trace_manager.traces:
            if trace.visible:
                curve = pg.PlotCurveItem(trace.data, pen=pg.mkPen(color=trace.color, width=trace.line_thickness))
                self.roi_plot_item.addItem(curve)

    def clear_traces(self):
        for curve in self.traces.values():
            self.plot_item.removeItem(curve)
            if curve in self.legend.items:
                self.legend.removeItem(curve)
        self.traces.clear()

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

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Initialize the Trace Manager
    trace_manager = TraceManager()

    # Set up the main window and Trace Plot
    main_window = QMainWindow()
    trace_plot = TracePlot(trace_manager)
    main_window.setCentralWidget(trace_plot)

    # Set up the Trace Dock
    trace_dock = TraceDock(main_window, trace_manager)
    main_window.addDockWidget(Qt.RightDockWidgetArea, trace_dock)

    trace_dock.deleteTraceRequest.connect(trace_manager.remove_trace)
    trace_dock.traceModeChanged.connect(lambda mode: setattr(trace_manager, 'trace_mode', mode))

    # Button to add random traces
    add_trace_button = QPushButton("Add Random Trace")
    add_trace_button.clicked.connect(lambda: trace_manager.process_trace_data({
        'data': np.random.normal(size=100),
        'color': pg.intColor(np.random.randint(0, 255), alpha=120),
        'line_thickness': 1,
        'mode': 'Group'  # Change this as needed for testing 'Isolate'
    }))

    # Dock widget for the controls
    controls_dock = QDockWidget("Controls", main_window)
    controls_dock.setWidget(add_trace_button)
    main_window.addDockWidget(Qt.RightDockWidgetArea, controls_dock)

    # Show the main window
    main_window.show()
    sys.exit(app.exec())