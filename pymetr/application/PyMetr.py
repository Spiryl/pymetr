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

from pymetr.application.instrument_panel import InstrumentManager, InstrumentPanel
from pymetr.application.trace_panel import TraceManager, TracePanel
from pymetr.application.display_panel import DisplayPanel, QuickPanel
from pymetr.application.trace_plot import TracePlot
from pymetr.core import Instrument, Trace

# TODO:  Build out MainMenuBar into its own class.
class MainMenuBar(QMenuBar):
    def __init__(self, parent=None):
        super(MainMenuBar, self).__init__(parent)

        # File menu
        self.fileMenu = self.addMenu("&File")
        self.instrumentMenu = self.addMenu("&Instruments")
        self.toolMenu = self.addMenu("&Tools")
        self.settingsMenu = self.addMenu("&Settings")

        # Add actions to the file menu
        self.setupFileMenuActions(parent)

        # Add actions to the file menu
        self.setupInstrumentMenuActions(parent)

    def setupFileMenuActions(self, parent):
        exportPlotAction = QAction("&Export Plot", self)
        exportPlotAction.triggered.connect(self.exportPlot)
        self.fileMenu.addAction(exportPlotAction)

        generateReportAction = QAction("&Generate Report", self)
        generateReportAction.triggered.connect(self.generateReport)
        self.fileMenu.addAction(generateReportAction)

        importTraceDataAction = QAction("&Import Trace Data", self)
        importTraceDataAction.triggered.connect(self.importTraceData)
        self.fileMenu.addAction(importTraceDataAction)

    def setupInstrumentMenuActions(self, parent):
        addInstrumentAction = QAction("&Add Instrument", self)
        addInstrumentAction.triggered.connect(parent.add_instrument_button_clicked)
        self.instrumentMenu.addAction(addInstrumentAction)

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

class InstrumentSelectionDialog(QDialog):
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
        logger.debug(f"Getting selected instrument")
        selected_item = self.listWidget.currentItem()
        if selected_item:
            return selected_item.text().split(' - ')[1]  # Returns the resource part of the item text
        return None

class DynamicInstrumentGUI(QMainWindow):
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

        ## --- Plot Dock ---------------------------------------
        self.plot_dock = QDockWidget("Plot Controls", self)
        self.plot_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.plot_dock.setMinimumWidth(250)
        self.addDockWidget(Qt.RightDockWidgetArea, self.plot_dock)

        self.plot_tabs = QTabWidget()
        self.plot_dock.setWidget(self.plot_tabs)

        # --- Trace Manager -------------------------------------
        self.trace_manager = TraceManager()

        # --- Trace Plot -------------------------------------
        self.trace_plot = TracePlot(self.trace_manager, self)
        self.layout.addWidget(self.trace_plot)

        # --- Trace Panel --------------------------------------
        self.trace_panel = TracePanel(self.trace_manager, self.trace_plot, self)
        self.plot_tabs.addTab(self.trace_panel, "Traces")

        # --- Display Panel ---------------------------------
        self.display_panel = DisplayPanel(self)
        self.plot_tabs.addTab(self.display_panel, "Display")
        
        ## --- Instrument Dock --------------------------------- 
        self.instrument_dock = QDockWidget("Instrument Controls", self)
        self.instrument_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.instrument_dock.setMinimumWidth(250)
        self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_dock)

        self.instrument_tabs = QTabWidget()
        self.instrument_dock.setWidget(self.instrument_tabs)

        # Tab the instrument dock beneath the plot dock
        self.tabifyDockWidget(self.plot_dock, self.instrument_dock)

        # --- Instrument Panel ---------------------------------
        self.instrument_manager = InstrumentManager()
        # self.instrument_panel = InstrumentPanel(self.instrument_manager, self)
        # self.instrument_panel.instrument_connected.connect(self.on_instrument_connected)
        # self.instrument_panel.instrument_disconnected.connect(self.on_instrument_disconnected)
        # self.instrument_panel.trace_data_ready.connect(self.trace_manager.add_trace)
        # self.instrument_tabs.addTab(self.instrument_panel, "Instrument 1")
        
        # --- Quick Panel  -------------------------------------
        self.quick_panel = QuickPanel(self)
        self.layout.addWidget(self.quick_panel)

        self.connect_signals()

    def connect_signals(self):
        # --- Trace Manager  -------------------------------------
        self.trace_manager.traceDataChanged.connect(self.trace_plot.update_plot)
        self.trace_manager.traceDataChanged.connect(self.trace_panel.update_parameter_tree)
        self.trace_manager.traceAdded.connect(self.trace_plot.update_roi_plot)

        # --- Display Panel  -------------------------------------
        self.display_panel.xGridChanged.connect(self.trace_plot.set_x_grid)
        self.display_panel.yGridChanged.connect(self.trace_plot.set_y_grid)
        self.display_panel.titleChanged.connect(self.trace_plot.set_title)
        self.display_panel.titleVisibilityChanged.connect(self.trace_plot.set_title_visible)
        self.display_panel.xLabelChanged.connect(self.trace_plot.set_x_label)
        self.display_panel.xLabelVisibilityChanged.connect(self.trace_plot.set_x_label_visible)
        self.display_panel.yLabelChanged.connect(self.trace_plot.set_y_label)
        self.display_panel.yLabelVisibilityChanged.connect(self.trace_plot.set_y_label_visible)

        # --- Display Panel  -------------------------------------
        self.quick_panel.addInstrumentClicked.connect(self.add_instrument_button_clicked)
        self.quick_panel.plotModeChanged.connect(self.trace_manager.set_plot_mode)
        self.quick_panel.roiPlotToggled.connect(self.trace_plot.on_roi_plot_enabled)
        self.quick_panel.roiPlotToggled.connect(self.trace_manager.emit_trace_data)
        self.quick_panel.traceModeChanged.connect(self.trace_manager.set_trace_mode)
        self.quick_panel.groupAllClicked.connect(self.on_group_all_clicked)
        self.quick_panel.isolateAllClicked.connect(self.on_isolate_all_clicked)
        self.quick_panel.testTraceClicked.connect(self.add_trace)
        self.quick_panel.clearTracesClicked.connect(self.on_clear_traces_clicked)
        self.quick_panel.screenshotClicked.connect(self.on_screenshot_clicked)
        self.quick_panel.clearTracesClicked.connect(self.trace_plot.clear_traces)


    # TODO: Move these methods to the controllers and keep 'main' for aggregation and signals. 
    def on_screenshot_clicked(self):
        # Create a QPixmap with the size of the graphics scene
        pixmap = QtGui.QPixmap(self.trace_plot.plot_layout.size())

        # Create a QPainter to paint on the pixmap
        painter = QtGui.QPainter(pixmap)

        # Render the graphics scene onto the painter
        self.trace_plot.plot_layout.render(painter)

        # End painting
        painter.end()

        # Set the pixmap as the clipboard content
        QtGui.QGuiApplication.clipboard().setPixmap(pixmap)

    def on_group_all_clicked(self):
        for trace in self.trace_manager.traces:
            trace.mode = "Group"
        self.trace_manager.emit_trace_data()

    def on_isolate_all_clicked(self):
        for trace in self.trace_manager.traces:
            trace.mode = "Isolate"
        self.trace_manager.emit_trace_data()

    def on_clear_traces_clicked(self):
        self.trace_manager.clear_traces()

    def add_trace(self):
        trace = TraceGenerator.generate_random_trace(self.trace_manager.trace_mode)
        self.trace_manager.add_trace(trace)

    def on_trace_mode_changed(self, trace_mode):
        self.trace_manager.trace_mode = trace_mode

    def add_instrument_button_clicked(self):
        logger.debug(f"Add instrument button clicked")
        logger.debug(f"Caller: {inspect.stack()[1][3]}")
        dialog = InstrumentSelectionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            selected_resource = dialog.get_selected_instrument()
            instrument, unique_id = self.instrument_manager.initialize_instrument(selected_resource)
            if instrument:
                # Create the instrument dock and tabs if they don't exist
                if not hasattr(self, 'instrument_dock'):
                    self.instrument_dock = QDockWidget("Instruments", self)
                    self.instrument_dock.setAllowedAreas(Qt.RightDockWidgetArea)
                    self.instrument_dock.setMinimumWidth(250)
                    self.instrument_tabs = QTabWidget()
                    self.instrument_dock.setWidget(self.instrument_tabs)
                    self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_dock)
                    self.tabifyDockWidget(self.tabbed_dock, self.instrument_dock)

                # Create a new instrument panel for the connected instrument
                new_instrument_panel = InstrumentPanel(self.instrument_manager, self)
                new_instrument_panel.setup_instrument_panel(instrument, unique_id)
                self.instrument_tabs.addTab(new_instrument_panel, unique_id)

                instrument_instance = self.instrument_manager.instruments[unique_id]['instance']
                instrument_instance.trace_data_ready.connect(self.trace_manager.add_trace)

    def on_instrument_connected(self, unique_id):
        instrument = self.instrument_manager.instruments[unique_id]['instance']
        logger.debug(f"Connecting trace_data_ready signal for instrument {unique_id}")
        logger.debug(f"Instrument {unique_id} connected.")

    def on_instrument_disconnected(self, unique_id):
        logger.debug(f"Instrument {unique_id} disconnected.")


class TraceGenerator:
    trace_counter = 1

    @staticmethod
    def generate_random_trace(mode='Group'):
        trace_name = f"Trace {TraceGenerator.trace_counter}"
        TraceGenerator.trace_counter += 1
        x = np.arange(1000)
        y = np.random.normal(loc=0, scale=20, size=1000)
        trace_dict = {
            'label': trace_name,
            'data': y.tolist(),
            'visible': True,
            'line_thickness': 1.0,
            'line_style': 'Solid'
        }
        return trace_dict
    
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