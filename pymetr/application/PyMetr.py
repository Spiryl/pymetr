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
import inspect
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from PySide6.QtGui import QColor, QAction
from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QDockWidget, QPushButton
from PySide6.QtWidgets import QWidget, QMainWindow, QFileDialog, QComboBox, QSizePolicy
from PySide6.QtWidgets import QMenuBar
from contextlib import contextmanager

from pymetr.application.instrument_dock import InstrumentDock
from pymetr.instrument import Instrument

class MainMenuBar(QMenuBar):
    def __init__(self, parent=None):
        super(MainMenuBar, self).__init__(parent)

        # File menu
        self.fileMenu = self.addMenu("&File")

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
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)

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

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)

        self.centralLayout = QVBoxLayout()
        self.centralWidget.setLayout(self.centralLayout)

        # --- Plot setup -------------------------------------
        self.plotLayout = pg.GraphicsLayoutWidget()
        self.centralLayout.addWidget(self.plotLayout, stretch=1)

        self.mainPlotItem = self.plotLayout.addPlot(row=0, col=0)
        self.mainPlot = self.mainPlotItem.vb
        self.roiPlotItem = self.plotLayout.addPlot(row=1, col=0, rowSpan=1, height=100)
        self.roiPlot = self.roiPlotItem.vb

        self.roi = pg.LinearRegionItem()
        self.roi.setZValue(-10)
        self.roiPlot.addItem(self.roi)

        self.roi.sigRegionChanged.connect(self.update_main_plot)
        self.mainPlot.sigXRangeChanged.connect(self.update_roi_plot)

        # --- Control Dock ---------------------------------
        self.centralControlDock = CentralControlDock(self)
        self.centralControlDock.addInstrumentButton.clicked.connect(self.add_instrument_button_clicked)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.centralControlDock)

        # --- Instrument Docks ---------------------------------
        self.instruments = {}  # Instrument Tracker
        self.instrumentDock = InstrumentDock(self)
        self.instrumentDock.instrument_connected.connect(self.on_instrument_connected)
        self.instrumentDock.instrument_disconnected.connect(self.on_instrument_disconnected)
        self.instrumentDock.trace_data_ready.connect(self.on_trace_data_ready)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.instrumentDock)
        
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

    def on_trace_data_ready(self, plot_data, unique_id=None):
        if unique_id is not None:
            logger.debug(f"Plotting trace data for instrument: {unique_id}.")
        else:
            logger.debug("Plotting trace data.")
        self.update_plot_data(plot_data)

    def update_plot_data(self, data):
        self.mainPlotItem.clear()
        self.roiPlotItem.clear()

        if isinstance(data, dict):
            for i, (trace_id, trace_info) in enumerate(data.items()):
                color = trace_info.get('color', self.color_palette[i % len(self.color_palette)])
                label = trace_info.get('label', f'Trace {i+1}')
                if trace_info.get('visible', True):
                    trace_data = trace_info.get('data', [])
                    trace_range = trace_info.get('range', np.arange(len(trace_data)))
                    main_curve = self.mainPlotItem.plot(trace_range, trace_data, pen=pg.mkPen(color, width=2), name=label)
                    self.mainPlot.addItem(main_curve)
                    roi_curve = self.roiPlotItem.plot(trace_range, trace_data, pen=pg.mkPen(color, width=2), name=label)
                    self.roiPlot.addItem(roi_curve)

        elif isinstance(data, (list, np.ndarray, tuple)):
            color = self.color_palette[0]
            label = 'Trace 1'
            if isinstance(data, tuple):
                main_curve = self.mainPlotItem.plot(data[1], data[0], pen=pg.mkPen(color, width=2), name=label)
                self.mainPlot.addItem(main_curve)
                roi_curve = self.roiPlotItem.plot(data[1], data[0], pen=pg.mkPen(color, width=2), name=label)
                self.roiPlot.addItem(roi_curve)
            else:
                main_curve = self.mainPlotItem.plot(data, pen=pg.mkPen(color, width=2), name=label)
                self.mainPlot.addItem(main_curve)
                roi_curve = self.roiPlotItem.plot(data, pen=pg.mkPen(color, width=2), name=label)
                self.roiPlot.addItem(roi_curve)

        else:
            logger.error(f"Received data in an unexpected format, unable to plot: {data}")

        self.update_main_plot()
        self.roiPlot.autoRange()

    def update_main_plot(self):
        self.mainPlot.setXRange(*self.roi.getRegion(), padding=0)

    def update_roi_plot(self):
        view_range = self.mainPlot.viewRange()[0]
        self.roi.setRegion(view_range)

if __name__ == "__main__":

    sys.argv += ['-platform', 'windows:darkmode=2']
    app = pg.mkQApp("Dynamic Instrument Control Application")
    app.setStyle("Fusion")

    # # Load and apply the stylesheet file
    # styleSheetFile = QtCore.QFile("pymetr/application/styles.qss")  # Update the path to where your QSS file is
    # if styleSheetFile.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text):
    #     textStream = QtCore.QTextStream(styleSheetFile)
    #     app.setStyleSheet(textStream.readAll())

    mainWindow = DynamicInstrumentGUI()
    mainWindow.show()
    sys.exit(app.exec())