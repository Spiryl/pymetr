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
        self.instrumentConnections = {}
        self.setWindowTitle("Dynamic Instrument Control")
        self.setGeometry(100, 100, 1200, 800)
        self.initUI()

    def initUI(self):

        self.initPlotWidget()
        self.initInstrumentDock()
        self.initPlotDock()
        self.initMenu()

    def initMenu(self):
            # Create actions to toggle the visibility of dock widgets
            self.viewMenu = self.menuBar().addMenu("&View")

            self.togglePlotDockAction = self.viewMenu.addAction("Plot Settings")
            self.togglePlotDockAction.setCheckable(True)
            self.togglePlotDockAction.setChecked(True)
            self.togglePlotDockAction.toggled.connect(self.plotDockWidget.setVisible)

            self.toggleInstrumentDockAction = self.viewMenu.addAction("Instrument Controls")
            self.toggleInstrumentDockAction.setCheckable(True)
            self.toggleInstrumentDockAction.setChecked(True)
            self.toggleInstrumentDockAction.toggled.connect(self.instrumentDockWidget.setVisible)

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

    def initInstrumentDock(self):
        self.instrumentDockWidget = QtWidgets.QDockWidget("Instrument Controls", self)
        self.instrumentDockWidget.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)

        instrumentWidget = QtWidgets.QWidget()
        instrumentLayout = QtWidgets.QVBoxLayout(instrumentWidget)

        # Example: Add a file selection button to load an instrument
        self.selectInstrumentButton = QtWidgets.QPushButton("Select Instrument")
        self.selectInstrumentButton.clicked.connect(self.engageInstrument)
        instrumentLayout.addWidget(self.selectInstrumentButton)

        self.instrumentParamTree = ParameterTree()
        instrumentLayout.addWidget(self.instrumentParamTree)

        self.instrumentDockWidget.setWidget(instrumentWidget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.instrumentDockWidget)

    def updateInstrumentConnection(self, model_number, serial_number, connect=True):
        unique_id = f"{model_number}_{serial_number}"
        if connect:
            # Connected state: Update UI to show connected status
            self.selectInstrumentButton.setText(f"{model_number} - {serial_number}".upper())
            self.selectInstrumentButton.setStyleSheet("background-color: green;")
            self.instrumentDockWidget.setWindowTitle(f"{model_number} - {serial_number}".upper())
        else:
            # Disconnected state: Attempt to close the connection and update UI
            if unique_id in self.instrumentConnections:
                instrument_handle = self.instrumentConnections[unique_id]
                try:
                    instrument_handle.close()
                    logger.info(f"Disconnected from {model_number} - {serial_number}")
                except Exception as e:
                    logger.error(f"Error disconnecting from instrument: {e}")
                del self.instrumentConnections[unique_id]  # Clean up the connection dictionary
                self.selectInstrumentButton.setText("Select Instrument")  # Reset button text
                self.selectInstrumentButton.setStyleSheet("")  # Clear any custom styles
                self.instrumentDockWidget.setWindowTitle("Instrument Controls")  # Reset dock title
                self.instrumentParamTree.clear()  # Clear the parameter tree

    def addInstrumentDock(self):
        # This could be connected to a menu action
        newDock = QtWidgets.QDockWidget(f"Instrument {self.instrumentDockCount}", self)
        newDock.setAllowedAreas(QtCore.Qt.AllDockWidgetAreas)
        # Setup similar to initInstrumentDock, tailored for the specific instrument
        # ...
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, newDock)
        self.instrumentDockCount += 1  # Keep track of how many you've added

    def engageInstrument(self):
        if self.selectInstrumentButton.text() != "Select Instrument":
            model_serial = self.selectInstrumentButton.text().split(" - ")
            model_number, serial_number = model_serial[0].lower(), model_serial[1]  # Assuming you want them back in lowercase for IDs
            unique_id = f"{model_number}_{serial_number}"
            logger.info(f"Disengage from instrument: {unique_id}")

            if unique_id in self.instrumentConnections:
                instrument_handle = self.instrumentConnections[unique_id]
                logger.info(f"Attempting to disconnect from instrument: {unique_id}")
                try:
                    instrument_handle.close()
                    logger.info(f"Disconnected from {model_number} - {serial_number}")
                except Exception as e:
                    logger.error(f"Error disconnecting from instrument: {e}")
                del self.instrumentConnections[unique_id]
                self.updateInstrumentConnection(model_number, serial_number, connect=False)
            return 
        
        instruments_data = Instrument.list_instruments("TCPIP?*::INSTR")
        dialog = InstrumentSelectionDialog(instruments_data, self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            selected_resource = dialog.selectedInstrument()
            if selected_resource:
                selected_key = [key for key, value in instruments_data[0].items() if value == selected_resource][0]
                idn_response = selected_key.split(": ")[1]
                model_number = idn_response.split(',')[1].strip().lower()

                filename = f"pymetr/instruments/{model_number}.py"
                if not os.path.exists(filename):
                    logger.info(f"No driver found for model {model_number}. Please select a driver file.")
                    filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Instrument Model File", "", "Python Files (*.py)")

                if filename:
                    module_name = os.path.splitext(os.path.basename(filename))[0]
                    spec = importlib.util.spec_from_file_location(module_name, filename)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, Instrument) and attr is not Instrument:
                            self.instr = attr(selected_resource)
                            break

                    if self.instr:
                        try:
                            self.instr.open()
                            serial_number = idn_response.split(',')[2].strip()
                            unique_id = f"{model_number}_{serial_number}"
                            self.instrumentConnections[unique_id] = self.instr
                            logger.info(f"Connected to instrument: {self.instr}")
                            self.ptree = factory.create_parameter_tree_from_file(filename)
                            self.ptree.sigTreeStateChanged.connect(self.on_tree_state_changed)
                            self.instrumentParamTree.setParameters(self.ptree, showTop=False)
                            self.instrumentParamTree.setAlternatingRowColors(True)
                            self.updateInstrumentConnection(model_number, serial_number, connect=True)
                        except Exception as e:
                            logger.error(f"Failed to open connection to instrument: {e}")
                    else:
                        logger.error("No instrument class found in the selected file.")
                else:
                    logger.info("Instrument selection cancelled.")
            else:
                logger.info("No instrument selected. Exiting...")

    def on_tree_state_changed(self, param, changes):
        logger.info("Tree changes detected.")
        for param, change, data in changes:
            # Extract the path to navigate to the right attribute
            path = self.ptree.childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()

            # Log the change details
            logger.debug(f"Parameter change - Name: {childName}, Change: {change}, Data: {data}")

            # Navigate and update the oscilloscope or its subsystems' property
            self.navigate_and_update_property(childName, data)
            logger.info(f"Property '{childName}' updated to '{data}'.")

    def navigate_and_update_property(self, path, value):
        # Split the path to access specific components, assuming first component can be skipped if it matches the instrument's name
        components = path.split('.')
        # components[0] would typically correspond to a subsystem or the instrument itself; start navigation from self.instr
        target = self.instr

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