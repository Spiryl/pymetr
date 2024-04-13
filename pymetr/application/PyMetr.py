import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger('pyvisa').setLevel(logging.CRITICAL)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(name)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'
import sys
import numpy as np
import random
import inspect
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from PySide6.QtGui import QColor, QAction
from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QDockWidget, QPushButton
from PySide6.QtWidgets import QWidget, QMainWindow, QFileDialog, QComboBox, QSizePolicy, QTabWidget
from PySide6.QtWidgets import QMenuBar
from PySide6.QtCore import QObject, Signal, Qt
from contextlib import contextmanager

from pymetr.application.instrument_dock import InstrumentDock
from pymetr.application.trace_dock import TraceDock
from pymetr.instrument import Instrument, Trace

class MainMenuBar(QMenuBar):
    def __init__(self, parent=None):
        super(MainMenuBar, self).__init__(parent)

        # File menu
        self.fileMenu = self.addMenu("&File")
        self.toolMenu = self.addMenu("&Tools")
        self.settingsMenu = self.addMenu("&Settings")

        # Add actions to the file menu
        self.setupFileMenuActions()

    def setupFileMenuActions(self):
        exportPlotAction = QAction("&Export Plot", self)
        exportPlotAction.triggered.connect(self.exportPlot)
        self.fileMenu.addAction(exportPlotAction)

        generateReportAction = QAction("&Generate Report", self)
        generateReportAction.triggered.connect(self.generateReport)
        self.fileMenu.addAction(generateReportAction)

        importTraceDataAction = QAction("&Import Trace Data", self)
        importTraceDataAction.triggered.connect(self.importTraceData)
        self.fileMenu.addAction(importTraceDataAction)

    # Placeholder methods for menu actions
    def exportPlot(self):
        # Placeholder for export plot logic
        print("Exporting plot...")

    def generateReport(self):
        # Placeholder for generate report logic
        print("Generating report...")

    def importTraceData(self):
        # Placeholder for import trace data logic
        print("Importing trace data...")

class CentralControlDock(QDockWidget):
    """
    This dock acts as a control panel with buttons for interacting with instruments.
    """

    def __init__(self, parent=None):
        """
        Initializes the control dock.
        """
        logger.debug(f"Initializing control dock")
        super(CentralControlDock, self).__init__("Control Panel", parent)
        self.setAllowedAreas(Qt.RightDockWidgetArea)

        self.dockLayout = QVBoxLayout()
        self.dockWidget = QWidget()
        self.dockWidget.setLayout(self.dockLayout)

        # Add Instrument Button
        self.addInstrumentButton = QPushButton("Add Instrument")
        self.addInstrumentButton.clicked.connect(parent.add_instrument_button_clicked)
        self.dockLayout.addWidget(self.addInstrumentButton)

        self.setWidget(self.dockWidget)

        # Adjust the dock's appearance
        self.dockLayout.addStretch()
        self.dockWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

class InstrumentSelectionDialog(QDialog):
    """
    Dialog for selecting an instrument from a list of available instruments.
    """
    def __init__(self, parent=None):
        logger.debug(f"Opening instrument selection dialog")
        super().__init__(parent)
        self.setWindowTitle("Select an Instrument")
        self.setGeometry(400, 400, 500, 300)
        self.layout = QVBoxLayout(self)
        
        self.listWidget = QListWidget()
        self.populate_instruments()
        self.layout.addWidget(self.listWidget)
        
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)
        
    def populate_instruments(self):
        """
        Populates the list widget with available instruments.
        """
        logger.debug(f"Populating Instruments")
        instruments_data = Instrument.list_instruments("TCPIP?*::INSTR")
        for unique_key, resource in instruments_data[0].items():
            # Extract the model number from the IDN response in the unique key
            try:
                idn_response = unique_key.split(": ")[1]
                model_number = idn_response.split(',')[1].strip()
                display_text = f"{model_number} - {resource}"
                self.listWidget.addItem(display_text)
            except IndexError:
                # Handle the case where the IDN response is not in the expected format
                continue    

    def get_selected_instrument(self):
        """
        Returns the selected instrument's details from the dialog.
        """
        logger.debug(f"Getting selected instrument")
        selected_item = self.listWidget.currentItem()
        if selected_item:
            return selected_item.text().split(' - ')[1]  # Returns the resource part of the item text
        return None

class DynamicInstrumentGUI(QMainWindow):
    """
    Main GUI window that integrates the plot, instrument control docks, and central control dock.
    """
    color_palette = ['#5E57FF', '#F23CA6', '#FF9535', '#4BFF36', '#02FEE4']

    def __init__(self):
        super().__init__()
        logger.debug(f"Opening PyMetr Application")
        self.setWindowTitle("PyMetr - Instrument Control")
        self.setGeometry(100, 100, 1200, 800)

        # --- Menu Bar ---------------------------------------
        self.menuBarInstance = MainMenuBar(self)
        self.setMenuBar(self.menuBarInstance)

        # --- Layout Setup -------------------------------------
        self.central_widget = QWidget()
        self.layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        # --- Plot setup -------------------------------------
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.layout.addWidget(self.plot_layout)
        self.plot_item = self.plot_layout.addPlot(row=0, col=0)
        self.plot_item.showGrid(x=True, y=True)
        self.legend = pg.LegendItem(offset=(70, 30))
        self.legend.setParentItem(self.plot_item)

        # --- Tabbed Dock for Trace and Instrument Docks -----
        self.tabbed_dock = QDockWidget("Control Dock", self)
        self.tabbed_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.tabbed_dock.setMinimumWidth(250)
        self.addDockWidget(Qt.RightDockWidgetArea, self.tabbed_dock)

        self.tabbed_widget = QTabWidget()
        self.tabbed_dock.setWidget(self.tabbed_widget)

        # --- Trace Dock --------------------------------------
        self.trace_dock = TraceDock(self)
        self.tabbed_widget.addTab(self.trace_dock, "Traces")

        # --- Instrument Dock ---------------------------------
        self.instrumentDock = InstrumentDock(self)
        self.instrumentDock.instrument_connected.connect(self.on_instrument_connected)
        self.instrumentDock.instrument_disconnected.connect(self.on_instrument_disconnected)
        self.instrumentDock.trace_data_ready.connect(self.on_trace_data_ready)
        self.tabbed_widget.addTab(self.instrumentDock, "Instruments")

        # --- Test Button -------------------------------------
        self.add_trace_button = QPushButton("Add Trace")
        self.add_trace_button.clicked.connect(self.add_trace)
        self.layout.addWidget(self.add_trace_button)

        self.additional_axes = []
        self.additional_view_boxes = []
        self.trace_view_boxes = {}  # Dictionary to store view boxes for each trace
        self.trace_axes = {}  # Dictionary to store axes for each trace
        self.traces = []

        self.roi_plot_item = None
        self.roi_plot = None
        self.roi = None

        self.plot_item.vb.sigRangeChanged.connect(self.on_main_plot_range_changed)
        self.trace_dock.trace_manager.traceDataChanged.connect(self.update_plot)  # Wrap this signal
        self.trace_dock.traceModeChanged.connect(self.on_trace_mode_changed)
        self.trace_dock.roiPlotEnabled.connect(self.on_roi_plot_enabled)

        # --- Control Dock ------------------------------------
        self.centralControlDock = CentralControlDock(self)
        self.centralControlDock.addInstrumentButton.clicked.connect(self.add_instrument_button_clicked)
        self.addDockWidget(Qt.RightDockWidgetArea, self.centralControlDock)

    def add_trace(self):
        trace = TraceGenerator.generate_random_trace(self.trace_dock.trace_manager.trace_mode)
        self.trace_dock.trace_manager.add_trace(trace)

    def add_instrument_button_clicked(self):
        """
        Called when the 'Add Instrument' button is clicked in the CentralControlDock.
        Initiates the instrument selection process.
        """
        logger.debug(f"Add instrument button clicked")
        logger.debug(f"Caller: {inspect.stack()[1][3]}")  # Log the calling method
        dialog = InstrumentSelectionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            selected_resource = dialog.get_selected_instrument()
            self.instrumentDock.setup_instrument(selected_resource)

    def on_instrument_connected(self, unique_id):
        """
        Called when an instrument is successfully connected.
        """
        logger.info(f"Instrument {unique_id} connected.")
        # Add any additional actions or UI updates here

    def on_instrument_disconnected(self, unique_id):
        """
        Called when an instrument is disconnected.
        """
        logger.info(f"Instrument {unique_id} disconnected.")
        # Add any additional actions or UI updates here

    def on_trace_data_ready(self, plot_data):
        self.update_plot(plot_data)

    def on_roi_plot_enabled(self, enabled):
        if enabled:
            self.roi_plot_item = self.plot_layout.addPlot(row=1, col=0)
            self.roi_plot_item.setMaximumHeight(100)  # Adjust the height of the ROI plot
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

    def update_roi_plot(self):
        if self.roi is not None:
            view_range = self.plot_item.vb.viewRange()[0]
            self.roi.setRegion(view_range)
    
    def add_trace(self):
        trace = TraceGenerator.generate_random_trace(self.trace_dock.trace_manager.trace_mode)
        self.trace_dock.trace_manager.add_trace(trace)

    def on_trace_mode_changed(self, trace_mode):
        self.trace_dock.trace_manager.trace_mode = trace_mode

    def update_plot(self, trace_data):
        self.plot_item.clear()
        self.clear_traces()  # Clear traces without removing additional axes
        if self.roi_plot_item is not None:
            self.roi_plot_item.clear()

        for trace in self.trace_dock.trace_manager.traces:
            visible = trace.visible
            color = trace.color
            legend_alias = trace.label
            x = np.arange(len(trace.data))
            y = trace.data
            mode = trace.mode

            if visible:
                pen = pg.mkPen(color=color, width=trace.line_thickness, style=self.get_line_style(trace.line_style))

                if mode == "Group":
                    curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                    self.plot_item.addItem(curve)
                    self.legend.addItem(curve, legend_alias)
                    self.traces.append(curve)
                else:  # Isolate mode
                    if trace in self.trace_view_boxes:
                        view_box = self.trace_view_boxes[trace]
                        axis = self.trace_axes[trace]
                    else:
                        axis = pg.AxisItem("right", pen=pen)
                        self.plot_layout.addItem(axis, row=0, col=self.trace_dock.trace_manager.traces.index(trace) + 1)
                        self.additional_axes.append(axis)

                        view_box = pg.ViewBox()
                        axis.linkToView(view_box)
                        view_box.setXLink(self.plot_item.vb)
                        self.plot_layout.scene().addItem(view_box)
                        self.additional_view_boxes.append(view_box)

                        self.trace_view_boxes[trace] = view_box
                        self.trace_axes[trace] = axis
                        view_box.sigRangeChanged.connect(lambda _, t=trace: self.handle_view_box_range_changed(view_box, t))  # Connect the range changed signal

                    curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                    view_box.addItem(curve)
                    self.legend.addItem(curve, legend_alias)
                    self.traces.append(curve)

                    if trace.y_range is not None:
                        view_box.setRange(yRange=trace.y_range)  # Restore the previous y-range
                        view_box.enableAutoRange(axis='y', enable=False)  # Disable y-axis auto-range
                    else:
                        view_box.setRange(yRange=self.plot_item.vb.viewRange()[1])  # Set initial y-range to match the main axis

                print(f"Trace: {trace.label}, Visible: {trace.visible}, Mode: {trace.mode}, Y-Range: {trace.y_range}")  # Debug information

        self.plot_item.vb.sigResized.connect(self.update_view_boxes)
        self.restore_view_ranges()  # Restore the view ranges of the main plot and additional axes
        self.update_roi_plot()
        self.update_view_boxes()

    def update_roi_plot(self):
        if self.roi_plot_item is not None:
            self.roi_plot_item.clear()

            for trace in self.trace_dock.trace_manager.traces:
                if trace.visible:
                    x = np.arange(len(trace.data))
                    y = trace.data
                    pen = pg.mkPen(color=trace.color, width=trace.line_thickness, style=self.get_line_style(trace.line_style))
                    roi_curve = self.roi_plot_item.plot(x, y, pen=pen, name=trace.label)

            self.roi_plot_item.autoRange()

    def clear_traces(self):
        for trace in self.traces:
            if trace in self.plot_item.items:
                self.plot_item.removeItem(trace)
            else:
                for view_box in self.trace_view_boxes.values():
                    if trace in view_box.addedItems:
                        view_box.removeItem(trace)
        self.traces.clear()
        self.legend.clear()

    def restore_view_ranges(self):
        if self.plot_item.vb.viewRange()[0] is not None:
            self.plot_item.vb.setRange(xRange=self.plot_item.vb.viewRange()[0], yRange=self.plot_item.vb.viewRange()[1], padding=0)
        for trace, view_box in self.trace_view_boxes.items():
            if trace.y_range is not None:
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
                if isinstance(t, Trace):  # Check if the element is a Trace object
                    t.x_range = x_range
                    t.y_range = y_range
                    print(f"Trace: {t.label}, X-Range: {x_range}, Y-Range: {y_range}")
                else:
                    print(f"Unexpected element in trace list: {t}")
        elif isinstance(trace, Trace):  # Check if trace is a single Trace object
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
        self.trace_view_boxes.clear()  # Clear the trace view boxes dictionary
        self.trace_axes.clear()  # Clear the trace axes dictionary

    def update_view_boxes(self):
        for view_box in self.additional_view_boxes:
            view_box.setGeometry(self.plot_item.vb.sceneBoundingRect())

class TraceGenerator:
    trace_counter = 1

    @staticmethod
    def generate_random_trace(mode='Group'):
        trace_name = f"Trace {TraceGenerator.trace_counter}"
        TraceGenerator.trace_counter += 1
        random_color = pg.intColor(random.randint(0, 255))
        x = np.arange(100)
        y = np.random.normal(loc=0, scale=20, size=100)
        trace = Trace(label=trace_name, color=random_color, mode=mode, data=y)
        return trace
    
if __name__ == "__main__":

    sys.argv += ['-platform', 'windows:darkmode=2']
    app = pg.mkQApp("Dynamic Instrument Control Application")
    app.setStyle("Fusion")

    # # Load and apply the stylesheet file
    # styleSheetFile = QFile("pymetr/application/styles.qss")  # Update the path to where your QSS file is
    # if styleSheetFile.open(QFile.ReadOnly | QFile.Text):
    #     textStream = QTextStream(styleSheetFile)
    #     app.setStyleSheet(textStream.readAll())

    mainWindow = DynamicInstrumentGUI()
    mainWindow.show()
    sys.exit(app.exec())