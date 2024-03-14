
import os

# Set the environment variable to prefer PySide6
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'
import sys
import numpy as np
import importlib.util
import logging
import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore
from pyqtgraph.parametertree import Parameter, ParameterTree
from factories import GuiFactory
from instrument import Instrument

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

factory = GuiFactory()

class DynamicInstrumentGUI(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dynamic Instrument Control")
        self.setGeometry(100, 100, 1200, 800)
        self.initUI()

    def initUI(self):
        self.mainWidget = QtWidgets.QWidget()
        self.setCentralWidget(self.mainWidget)
        self.layout = QtWidgets.QVBoxLayout(self.mainWidget)

        self.initPlotWidget()
        self.initDockWidgets()

    def initPlotWidget(self):
        self.plotWidget = pg.PlotWidget()
        self.layout.addWidget(self.plotWidget)

    def initDockWidgets(self):
        self.controlDockWidget = QtWidgets.QDockWidget("Instrument Controls", self)
        self.controlDockWidget.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)

        self.controlWidget = QtWidgets.QWidget()
        self.controlLayout = QtWidgets.QVBoxLayout(self.controlWidget)

        # Place the Update Plot button in the dock as well
        self.plotUpdateButton = QtWidgets.QPushButton("Update Plot")
        self.plotUpdateButton.clicked.connect(self.updatePlot)
        self.controlLayout.addWidget(self.plotUpdateButton)

        # Add a file selection button
        self.fileSelectButton = QtWidgets.QPushButton("Select Instrument File")
        self.fileSelectButton.clicked.connect(self.loadInstrumentFile)
        self.controlLayout.addWidget(self.fileSelectButton)

        self.paramTree = ParameterTree()
        self.controlLayout.addWidget(self.paramTree)

        self.controlDockWidget.setWidget(self.controlWidget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.controlDockWidget)

    def updatePlot(self):
        self.plotWidget.clear()

        x = np.linspace(0, 2 * np.pi, 10000)
        y = 5 * np.sin(36 * x) + np.random.normal(size=10000)
        self.plotWidget.plot(x, y, pen='g')

    def loadInstrumentFile(self):

        filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Instrument Model File", "", "Python Files (*.py)")
        if filename:
            # Dynamically import the module based on the selected file
            module_name = os.path.splitext(os.path.basename(filename))[0]
            spec = importlib.util.spec_from_file_location(module_name, filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Search for the instrument class in the module and instantiate it
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, Instrument) and attr is not Instrument:
                    self.instr = attr(Instrument.select_instrument("TCPIP?*::INSTR")) 
                    break

            # Open a connection with the instrument
            if self.instr:
                try:
                    self.instr.open()
                    logger.info(f"Connected to instrument: {self.instr}")
                    # Use GuiFactory to create and set the parameter tree from file
                    self.ptree = factory.create_parameter_tree_from_file(filename)
                    self.ptree.sigTreeStateChanged.connect(self.on_tree_state_changed)
                    self.paramTree.setParameters(self.ptree, showTop=False)
                    self.paramTree.setAlternatingRowColors(True)
                except Exception as e:
                    logger.error(f"Failed to open connection to instrument: {e}")
            else:
                logger.error("No instrument class found in the selected file.")

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

if __name__ == "__main__":

    # sys.argv += ['-platform', 'windows:darkmode=2']
    app = pg.mkQApp("Dynamic Instrument Control Application")
    app.setStyle("Fusion")

    # # Load and apply the stylesheet file
    # styleSheetFile = QtCore.QFile("styles.qss")  # Update the path to where your QSS file is
    # if styleSheetFile.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text):
    #     textStream = QtCore.QTextStream(styleSheetFile)
    #     app.setStyleSheet(textStream.readAll())

    mainWindow = DynamicInstrumentGUI()
    mainWindow.show()
    sys.exit(app.exec_())
