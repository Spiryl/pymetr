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
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QDockWidget, QPushButton
from PySide6.QtWidgets import QWidget, QMainWindow, QFileDialog, QComboBox, QSizePolicy
from contextlib import contextmanager

from pymetr.application.instrument_dock import InstrumentDock
from pymetr.instrument import Instrument

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
        """
        Initializes the main GUI window and its components, including the instruments dictionary and central control dock.
        """
        super().__init__()
        logger.debug(f"Opening PyMetr Application")
        self.setWindowTitle("Dynamic Instrument Control")
        self.setGeometry(100, 100, 1200, 800)
        
        self.instruments = {} # Instrument Tracker

        self.plotWidget = pg.PlotWidget() 
        self.setCentralWidget(self.plotWidget)
        
        self.centralControlDock = CentralControlDock(self) 
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.centralControlDock)

        self.instrumentDock = InstrumentDock(self)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.instrumentDock)

        # Connect signals and slots
        self.centralControlDock.addInstrumentButton.clicked.connect(self.add_instrument_button_clicked)
        self.instrumentDock.instrument_connected.connect(self.on_instrument_connected)
        self.instrumentDock.instrument_disconnected.connect(self.on_instrument_disconnected)
        self.instrumentDock.trace_data_ready.connect(self.on_trace_data_ready)

    def add_instrument_button_clicked(self):
        """
        Called when the 'Add Instrument' button is clicked in the CentralControlDock.
        Initiates the instrument selection process.
        """
        logger.debug(f"Add instrument button clicked")
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
        self.update_plot(plot_data)

    def update_plot(self, data):
        plot_widget = self.plotWidget  # Access the plot widget from the instance
        plot_widget.clear()
        plot_widget.showGrid(x=True, y=True, alpha=0.3)  # Show grid by default
        plot_widget.addLegend()  # Show legend by default

        # If data is a dictionary, iterate through items
        if isinstance(data, dict):
            for i, (trace_id, trace_info) in enumerate(data.items()):
                color = trace_info.get('color', self.color_palette[i % len(self.color_palette)])
                label = trace_info.get('label', f'Trace {i+1}')
                if trace_info.get('visible', True):  # Check if the trace should be visible
                    trace_data = trace_info.get('data', [])
                    trace_range = trace_info.get('range', np.arange(len(trace_data)))
                    plot_widget.plot(trace_range, trace_data, pen=pg.mkPen(color, width=2), name=label)

        # If data is not a dictionary, plot it directly
        elif isinstance(data, (list, np.ndarray, tuple)):
            color = self.color_palette[0]  # Start with the first color in the palette
            label = 'Trace 1'
            if isinstance(data, tuple):
                plot_widget.plot(data[1], data[0], pen=pg.mkPen(color, width=2), name=label)
            else:
                plot_widget.plot(data, pen=pg.mkPen(color, width=2), name=label)

        else:
            logger.error(f"Received data in an unexpected format, unable to plot: {data}")

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