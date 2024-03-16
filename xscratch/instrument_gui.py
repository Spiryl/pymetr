import os
# Set the environment variable to prefer PySide6
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'
import sys
import numpy as np
import importlib.util
import logging
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from pyqtgraph.parametertree import Parameter, ParameterTree
from factories import GuiFactory
from instrument import Instrument

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

factory = GuiFactory()

class InstrumentSelectionDialog(QtWidgets.QDialog):
    def __init__(self, instruments_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select an Instrument")
        self.layout = QtWidgets.QVBoxLayout(self)
        self.instrument_map = {}
        self.listWidget = QtWidgets.QListWidget()

        unique_instruments, _ = instruments_data
        for unique_key, resource in unique_instruments.items():
            # Extract the model number from the IDN response in the unique key
            try:
                idn_response = unique_key.split(": ")[1]  # IDN response is after the first colon-space
                model_number = idn_response.split(',')[1].strip()  # Model number is the second item in the IDN response
                display_text = f"{model_number} - {resource}"
                self.listWidget.addItem(display_text)
                self.instrument_map[display_text] = resource
            except IndexError:
                # Handle the case where the IDN response is not in the expected format
                continue

        self.layout.addWidget(self.listWidget)
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

    def selectedInstrument(self):
        display_text = self.listWidget.currentItem().text() if self.listWidget.currentItem() else None
        return self.instrument_map.get(display_text, None)
    
class DynamicInstrumentGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.instruments = {}  # Dictionary to hold all instrument-related UI components and data
        self.instrumentDockCount = 1
        self.setWindowTitle("Dynamic Instrument Control")
        self.setGeometry(100, 100, 1200, 800)
        self.initUI()

    def initUI(self):

        self.initPlotWidget()
        self.initPlotDock()
        self.initMenu()

    def initMenuBar(self):
        # Create the menu bar and add an 'Instrument' menu
        instrumentMenu = self.menuBar().addMenu("&Instrument")

        # Add an action for adding a new instrument
        addInstrumentAction = QtWidgets.QAction("Add Instrument", self)
        addInstrumentAction.setShortcut('Ctrl+N')  # For the hot-key
        addInstrumentAction.triggered.connect(self.selectAndConnectInstrument)

        instrumentMenu.addAction(addInstrumentAction)

    def selectAndConnectInstrument(self):
        instruments_data = Instrument.list_instruments("TCPIP?*::INSTR")
        dialog = InstrumentSelectionDialog(instruments_data, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_resource = dialog.selectedInstrument()
            if selected_resource:
                selected_key = [key for key, value in instruments_data[0].items() if value == selected_resource][0]
                idn_response = selected_key.split(": ")[1]
                # Pass the resource and response to the method that creates the dock
                self.createAndPopulateInstrumentDock(selected_resource, idn_response)

    def initPlotWidget(self):
        self.plotWidget = pg.PlotWidget()
        self.setCentralWidget(self.plotWidget)  # Set the plotWidget as the central widget

        # Ensure the button moves correctly on resize
        # self.plotWidget.resizeEvent = self.handlePlotWidgetResize

    def handlePlotWidgetResize(self, event):
        # Make sure the update button stays in the top right corner on resize
        self.plotUpdateButton.move(self.plotWidget.width() - self.plotUpdateButton.width() - 10, 10)
        event.accept()

    def initPlotDock(self):
        self.plotDockWidget = QtWidgets.QDockWidget("Plot Settings", self)
        self.plotDockWidget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)

        plotSettingsWidget = QtWidgets.QWidget()
        plotSettingsLayout = QtWidgets.QVBoxLayout(plotSettingsWidget)

        # Update Plot button at the very top
        self.plotUpdateButton = QtWidgets.QPushButton("Update Plot")
        self.plotUpdateButton.clicked.connect(self.updatePlot)
        plotSettingsLayout.addWidget(self.plotUpdateButton)

        # Parameter Tree for Plot Settings
        # We create the ParameterTree
        children = [
            dict(name='make_line_glow', type='bool', value=False),
            dict(name='add_underglow', type='list', limits=['None', 'Full', 'Gradient'], value='None'),
            dict(name='nb_lines', type='int', limits=[1, 6], value=1),
            dict(name='nb glow lines', type='int', limits=[0, 15], value=10),
            dict(name='alpha_start', type='int', limits=[0, 255], value=25, step=1),
            dict(name='alpha_stop', type='int', limits=[0, 255], value=25, step=1),
            dict(name='alpha_underglow', type='int', limits=[0, 255], value=25, step=1),
            dict(name='linewidth_start', type='float', limits=[0.1, 50], value=1, step=0.1),
            dict(name='linewidth_stop', type='float', limits=[0.2, 50], value=8, step=0.1),
        ]

        self.plotParams = Parameter.create(name='Plot Parameters', type='group', children=children)
        self.plotParams.sigTreeStateChanged.connect(self.updatePlot)
        self.plotParamTree = ParameterTree()
        self.plotParamTree.setParameters(self.plotParams, showTop=False)
        plotSettingsLayout.addWidget(self.plotParamTree)

        self.plotDockWidget.setWidget(plotSettingsWidget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.plotDockWidget)

    def addInstrumentDock(self):
        unique_id = f"Instrument_{self.instrumentDockCount}"
        dockWidget = QtWidgets.QDockWidget(f"Instrument Controls {self.instrumentDockCount}", self)
        dockWidget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)

        instrumentWidget = QtWidgets.QWidget()
        instrumentLayout = QtWidgets.QVBoxLayout(instrumentWidget)

        selectInstrumentButton = QtWidgets.QPushButton("Select Instrument")
        # Pass the dockWidget itself to engageInstrument
        selectInstrumentButton.clicked.connect(lambda: self.engageInstrument(dockWidget))
        instrumentLayout.addWidget(selectInstrumentButton)

        instrumentParamTree = ParameterTree()
        instrumentLayout.addWidget(instrumentParamTree)

        dockWidget.setWidget(instrumentWidget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, dockWidget)

        self.instruments[unique_id] = {
            'dockWidget': dockWidget,
            'selectButton': selectInstrumentButton,
            'paramTree': instrumentParamTree,
            'connection': None
        }

        self.instrumentDockCount += 1

    def removeInstrumentDock(self, unique_id):
        if unique_id in self.instruments:
            _instrument = self.instruments[unique_id]
            if _instrument["connection"]:
                try:
                    _instrument["connection"].close()  # Close the connection if it exists
                except Exception as e:
                    logger.error(f"Error closing connection for {unique_id}: {e}")
            _instrument["dockWidget"].close()  # Close and remove the dock widget
            del self.instruments[unique_id]  # Remove the entry from the dictionary

    def updateInstrumentConnection(self, unique_id, connect=True):
        if unique_id not in self.instruments:
            logger.error(f"Unique ID {unique_id} not found in instrument dictionary.")
            return

        _instrument = self.instruments[unique_id]

        if connect:
            # Connected state: Update UI to show connected status
            _instrument['selectButton'].setText(f"{unique_id.split('_')[0]} - {unique_id.split('_')[1]}".upper())
            _instrument['selectButton'].setStyleSheet("background-color: green;")
            _instrument['dockWidget'].setWindowTitle(f"{unique_id.split('_')[0]} - {unique_id.split('_')[1]}".upper())
        else:
            # Disconnected state: Attempt to close the connection and update UI
            if 'connection' in _instrument and _instrument['connection']:
                try:
                    _instrument['connection'].close()
                    logger.info(f"Disconnected from {unique_id}")
                except Exception as e:
                    logger.error(f"Error disconnecting from instrument: {e}")
                _instrument['connection'] = None  # Consider setting connection to None instead of deleting the entry
            # Reset UI components to default
            _instrument['selectButton'].setText("Select Instrument")
            _instrument['selectButton'].setStyleSheet("")
            _instrument['dockWidget'].setWindowTitle("Instrument Controls")
            # If your ParameterTree doesn’t have a clear method, consider resetting it in another way
            _instrument['paramTree'].clear()  # This line might need adjustment
            del self.instruments[unique_id]

    def closeInstrument(self, unique_id):
        _instrument = self.instruments.get(unique_id)
        if not _instrument:
            logger.error("Instrument info not found.")
            return

        logger.info(f"Disengage from instrument: {unique_id}")
        try:
            _instrument['connection'].close()
            logger.info(f"Disconnected from {unique_id}")
        except Exception as e:
            logger.error(f"Error disconnecting from instrument: {e}")

        # Reset UI components
        _instrument['selectButton'].setText("Select Instrument")
        _instrument['selectButton'].setStyleSheet("")
        _instrument['dockWidget'].setWindowTitle("Instrument Controls")
        _instrument['paramTree'].clear()

        # Remove the instrument from the dictionary
        del self.instruments[unique_id]

    def loadInstrumentDriver(self, model_number):
        filename = f"pymetr/instruments/{model_number}.py"
        if not os.path.exists(filename):
            logger.info(f"No driver found for model {model_number}. Please select a driver file.")
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Instrument Model File", "", "Python Files (*.py)")
            if not filename:  # User cancelled file selection
                return None
        
        logger.info(f"Driver found for model {model_number}. Initializing....")
        module_name = os.path.splitext(os.path.basename(filename))[0]
        spec = importlib.util.spec_from_file_location(module_name, filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        instrument_class = next(
            (attr for attr_name, attr in module.__dict__.items() if isinstance(attr, type) and issubclass(attr, Instrument) and attr is not Instrument),
            None
        )
        
        if instrument_class is None:
            logger.error("No instrument class found in the selected file.")
            return None

        return instrument_class
    
    def openInstrumentConnection(self, instrument_class, selected_resource, unique_id):
        try:
            instrument = instrument_class(selected_resource)
            instrument.open()
            logger.info(f"Connected to instrument: {instrument}")
            return instrument
        except Exception as e:
            logger.error(f"Failed to open and build instrument model: {e}")
            return None
        
    def setupInstrumentParameters(self, filename, unique_id, instrument):
        _parameters = factory.create_parameter_tree_from_file(filename)
        _paramTree = self.instruments[unique_id]['paramTree']
        
        _paramTree.setParameters(_parameters, showTop=False)
        _paramTree.setAlternatingRowColors(True)
        
        _parameters.sigTreeStateChanged.connect(
            lambda param, changes, unique_id=unique_id: self.on_tree_state_changed(param, changes, unique_id)
        )
    
    def openInstrument(self, selected_resource, idn_response, temp_unique_id):
        model_number = idn_response.split(',')[1].strip().lower()
        instrument_class = self.loadInstrumentDriver(model_number)
        if instrument_class is None:
            return  # Stop if no driver is found or selected
        
        serial_number = idn_response.split(',')[2].strip()
        unique_id = f"{model_number}_{serial_number}"
        
        instrument = self.openInstrumentConnection(instrument_class, selected_resource, unique_id)
        if instrument is None:
            return  # Stop if connection failed
        
        # After a successful connection:
        serial_number = idn_response.split(',')[2].strip()
        model_number = idn_response.split(',')[1].strip().lower()
        unique_id = f"{model_number}_{serial_number}"

        # Now, you need to update the dock entry to reflect this unique_id
        # First, get the current dock entry based on its temp_unique_id
        dock_entry = self.instruments.pop(temp_unique_id, None)
        
        if dock_entry:
            # Update the entry with the actual unique_id
            self.instruments[unique_id] = dock_entry
            logger.info(f"Updated dock entry from {temp_unique_id} to {unique_id}.")
        else:
            logger.error(f"Failed to find and update dock entry for {temp_unique_id}.")
        
        _instrument = self.instruments.get(unique_id, None)
        if _instrument is None:
            logger.error(f"No instrument entry found for unique_id: {unique_id}")
            return
        
        _instrument['connection'] = instrument
        self.setupInstrumentParameters(model_number, unique_id, instrument)
        
        self.updateInstrumentConnection(unique_id, connect=True)

    def engageInstrument(self, temp_unique_id):
        _instrument = self.instruments.get(temp_unique_id, {})
        if _instrument.get('connection'):  # If an instrument is connected, close it
            self.closeInstrument(temp_unique_id)
        else:  # If no instrument is connected, proceed to open a new connection
            instruments_data = Instrument.list_instruments("TCPIP?*::INSTR")
            dialog = InstrumentSelectionDialog(instruments_data, self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                selected_resource = dialog.selectedInstrument()
                if selected_resource:
                    selected_key = [key for key, value in instruments_data[0].items() if value == selected_resource][0]
                    idn_response = selected_key.split(": ")[1]
                    # Now pass temp_unique_id along to openInstrument
                    self.openInstrument(selected_resource, idn_response, temp_unique_id)
                else:
                    logger.info("No instrument selected. Exiting...")

    def on_tree_state_changed(self, param, changes, unique_id):
        logger.info(f"Tree changes detected for instrument {unique_id}.")
        for param, change, data in changes:
            # Extract the path to navigate to link to the correct attribute
            _instrument = self.instruments[unique_id]
            path = _instrument['paramTree'].childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()

            logger.debug(f"Parameter change - Name: {childName}, Change: {change}, Data: {data}")

            self.navigate_and_update_property(childName, data, unique_id)
            logger.info(f"Property '{childName}' updated to '{data}'.")

    def navigate_and_update_property(self, path, value, unique_id):
        components = path.split('.')
        target = self.instruments[unique_id]['connection']

        for comp in components[:-1]:  # Exclude the last component as it's the property to update
            if hasattr(target, comp.lower()):  # Convert to lowercase to match your naming convention
                target = getattr(target, comp.lower())
            else:
                logger.error(f"Component '{comp}' not found in path '{path}'. Stopping navigation.")
                return

        # Last component should be the property name
        property_name = components[-1]
        if hasattr(target, property_name):
            setattr(target, property_name, value)
            logger.info(f"Successfully updated '{property_name}' in '{components[:-1]}' to '{value}'.")
        else:
            logger.error(f"Property '{property_name}' not found in target '{target.__class__.__name__}'.")

    def updatePlot(self):
        self.plotWidget.clear()

        nb_glow_lines   = self.plotParams.child('nb glow lines').value()
        alpha_start     = self.plotParams.child('alpha_start').value()
        alpha_stop      = self.plotParams.child('alpha_stop').value()
        alpha_underglow = self.plotParams.child('alpha_underglow').value()
        linewidth_start = self.plotParams.child('linewidth_start').value()
        linewidth_stop  = self.plotParams.child('linewidth_stop').value()
        nb_lines        = self.plotParams.child('nb_lines').value()

        xs = []
        ys = []
        for i in range(nb_lines):
            xs.append(np.linspace(0, 2*np.pi, 100)-i)
            ys.append(np.sin(xs[-1])*xs[-1]-i/0.3)

        # For each line we:
        # 1. Add a PlotDataItem with the pen and brush corresponding to the line
        #    color and the underglow
        # 2. Add nb_glow_lines PlotDatamItem with increasing width and low alpha
        #    to create the glow effect
        # Dedicated colors which look "good"
        colors = ['#08F7FE', '#FE53BB', '#F5D300', '#00ff41', '#FF0000', '#9467bd', ]

        for color, x, y in zip(colors, xs, ys):
            pen = pg.mkPen(color=color)
            if self.plotParams.child('add_underglow').value()=='Full':
                kw={'fillLevel' : 0.0,
                    'fillBrush' : pg.mkBrush(color='{}{:02x}'.format(color, alpha_underglow)),
                    }
            elif self.plotParams.child('add_underglow').value()=='Gradient':
                grad = QtGui.QLinearGradient(x.mean(), y.min(), x.mean(), y.max())
                grad.setColorAt(0.001, pg.mkColor(color))
                grad.setColorAt(abs(y.min())/(y.max()-y.min()), pg.mkColor('{}{:02x}'.format(color, alpha_underglow)))
                grad.setColorAt(0.999, pg.mkColor(color))
                brush = QtGui.QBrush(grad)
                kw={'fillLevel' : 0.0,
                    'fillBrush' : brush,
                    }
            else:
                kw = {}
            self.plotWidget.addItem(pg.PlotDataItem(x, y, pen=pen, **kw))

            if self.plotParams.child('make_line_glow').value():
                alphas = np.linspace(alpha_start, alpha_stop, nb_glow_lines, dtype=int)
                line_widths = np.linspace(linewidth_start, linewidth_stop, nb_glow_lines)

                for alpha, lw in zip(alphas, line_widths):
                    pen = pg.mkPen(color='{}{:02x}'.format(color, alpha), width=lw, connect="finite")
                    self.plotWidget.addItem(pg.PlotDataItem(x, y, pen=pen))

if __name__ == "__main__":

    # sys.argv += ['-platform', 'windows:darkmode=2']
    app = pg.mkQApp("Dynamic Instrument Control Application")
    app.setStyle("Fusion")

    # Load and apply the stylesheet file
    styleSheetFile = QtCore.QFile("pymetr/styles/styles.qss")  # Update the path to where your QSS file is
    if styleSheetFile.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text):
        textStream = QtCore.QTextStream(styleSheetFile)
        app.setStyleSheet(textStream.readAll())

    mainWindow = DynamicInstrumentGUI()
    mainWindow.show()
    sys.exit(app.exec())