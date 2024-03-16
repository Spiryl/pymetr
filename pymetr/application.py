import os
# Set the environment variable to prefer PySide6
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'
import sys
import numpy as np
import importlib.util
import logging
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.parametertree import Parameter, ParameterTree
from factories import GuiFactory
from instrument import Instrument
from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QDockWidget, QPushButton, QWidget, QMainWindow, QFileDialog

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

factory = GuiFactory()

class CentralControlDock(QDockWidget):
    """
    This dock acts as a control panel with buttons for interacting with instruments.
    """

    def __init__(self, parent=None):
        """
        Initializes the control dock.
        """
        super(CentralControlDock, self).__init__("Control Panel", parent)
        self.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)

        # Main control dock widget layout
        self.dockLayout = QVBoxLayout()
        self.dockWidget = QWidget()
        self.dockWidget.setLayout(self.dockLayout)

        # Add Instrument Button
        self.addInstrumentButton = QPushButton("Add Instrument")
        self.addInstrumentButton.clicked.connect(parent.add_instrument_button_clicked)  # Assumes a method in the parent to handle the click
        self.dockLayout.addWidget(self.addInstrumentButton)

        self.setWidget(self.dockWidget)

class InstrumentSelectionDialog(QDialog):
    """
    Dialog for selecting an instrument from a list of available instruments.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select an Instrument")
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
        selected_item = self.listWidget.currentItem()
        if selected_item:
            return selected_item.text().split(' - ')[1]  # Returns the resource part of the item text
        return None

class InstrumentParameterDock(QDockWidget):
    """
    Dock widget to display and control the parameters of a connected instrument.
    """
    def __init__(self, instrument, parent=None, on_tree_state_changed=None):
        """
        Initializes the parameter dock for a specific instrument.
        """
        super(InstrumentParameterDock, self).__init__(parent)
        self.setWindowTitle(f"{instrument}".upper())
        self.on_tree_state_changed = on_tree_state_changed

        # Main widget and layout
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        # Other UI elements, like ParameterTree, will be set up here

        self.setWidget(self.widget)

    def setup_parameters(self, parameters):
        """
        Receives a parameter tree and displays it within the dock.
        """
        self.parameters = parameters
        self.parameterTree = ParameterTree()
        self.layout.addWidget(self.parameterTree)
        self.parameterTree.setAlternatingRowColors(False)
        self.parameterTree.setParameters(parameters, showTop=True)
        if self.on_tree_state_changed:
            self.parameters.sigTreeStateChanged.connect(self.on_tree_state_changed)

class DynamicInstrumentGUI(QMainWindow):
    """
    Main GUI window that integrates the plot, instrument control docks, and central control dock.
    """

    def __init__(self):
        """
        Initializes the main GUI window and its components, including the instruments dictionary and central control dock.
        """
        super().__init__()
        self.setWindowTitle("Dynamic Instrument Control")
        self.setGeometry(100, 100, 1200, 800)
        
        self.instruments = {} # Instrument Tracker

        self.plotWidget = pg.PlotWidget() # Main plot widget
        self.setCentralWidget(self.plotWidget)  
        
        self.centralControlDock = CentralControlDock(self) # Main control dock
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.centralControlDock)

    def add_instrument_button_clicked(self):
        """
        Called when the 'Add Instrument' button is clicked in the CentralControlDock.
        Initiates the instrument selection process.
        """
        dialog = InstrumentSelectionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            selected_resource = dialog.get_selected_instrument()
            print(f"Selected instrument: {selected_resource}")
            self.setup_instrument(selected_resource)

    def setup_instrument(self, selected_resource):
        """
        Engages with the selected instrument by loading its driver,
        opening a connection, and setting up its parameters in the UI.
        """
        selected_key = [key for key, value in Instrument.list_instruments("TCPIP?*::INSTR")[0].items() if value == selected_resource][0]
        idn_response = selected_key.split(": ")[1]
        model_number = idn_response.split(',')[1].strip().lower()
        serial_number = idn_response.split(',')[2].strip()
        unique_id = f"{model_number}_{serial_number}"

        # Initialize instrument record in the dictionary
        self.instruments[unique_id] = {
            'model_number': model_number,
            'serial_number': serial_number,
            # Placeholder for additional details to be added later
        }

        _driver = f"pymetr/drivers/{model_number}.py"
        if not os.path.exists(_driver):
            logger.info(f"No driver found for model {model_number}. Please select a driver file.")
            _driver, _ = QFileDialog.getOpenFileName(self, "Select Instrument Model File", "", "Python Files (*.py)")

        if _driver:
            module = self.load_instrument_driver(_driver)
            if module:
                self.initialize_and_configure_instrument(module, selected_resource, unique_id, _driver)

    def load_instrument_driver(self, _driver):
        """
        Loads the instrument driver from the given _driver.
        """
        module_name = os.path.splitext(os.path.basename(_driver))[0]
        spec = importlib.util.spec_from_file_location(module_name, _driver)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(f"Error loading instrument driver '{_driver}': {e}")
            return None

    def initialize_and_configure_instrument(self, module, selected_resource, unique_id, _driver):
        """
        Initializes the instrument using the loaded driver module, opens a connection,
        and sets up the instrument parameter UI using the GuiFactory.
        """
        instr_class = None
        
        # Identify the correct instrument class from the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Instrument) and attr != Instrument:
                instr_class = attr
                break

        if instr_class:
            try:
                instr = instr_class(selected_resource)
                instr.open()
                parameters = factory.create_parameters_from_driver(_driver, instr)

                parameter_dock = InstrumentParameterDock(unique_id, self, on_tree_state_changed=self.create_parameter_change_handler(unique_id))
                parameter_dock.setup_parameters(parameters)
                self.addDockWidget(QtCore.Qt.RightDockWidgetArea, parameter_dock)
                self.instruments[unique_id]['dock'] = parameter_dock
                self.instruments[unique_id]['instance'] = instr
                self.instruments[unique_id]['parameters'] = parameters
            except Exception as e:
                logger.error(f"Failed to initialize instrument {unique_id}: {e}")
        else:
            logger.error("Driver module for {unique_id} does not support instance creation.")

    def create_parameter_change_handler(self, unique_id):
        def parameter_changed(param, changes):
            # Here, implement what happens when a parameter changes.
            # This function will have access to 'unique_id' in its closure.
            self.on_tree_state_changed(param, changes, unique_id)
        return parameter_changed

    def on_tree_state_changed(self, param, changes, unique_id):
        logger.info(f"Tree changes detected for instrument {unique_id}.")
        for param, change, data in changes:
            _instrument = self.instruments[unique_id]
            path = _instrument['parameters'].childPath(param)
            if path is not None:
                childName = '.'.join(path)
            else:
                childName = param.name()

            logger.debug(f"Parameter change - Name: {childName}, Change: {change}, Data: {data}")
            self.navigate_and_update_property(childName, data, unique_id)
            logger.info(f"Property '{childName}' updated to '{data}'.")

    def navigate_and_update_property(self, path, value, unique_id):
        components = path.split('.')
        target = self.instruments[unique_id]['instance']

        # Navigate to the target component
        for comp in components[:-1]:
            comp = comp.lower()  # Convert component to lowercase to match instance storage
            if hasattr(target, comp):
                target = getattr(target, comp)
            else:
                logger.error(f"Component '{comp}' not found in path '{path}'. Stopping navigation.")
                return

        # The last component is the property or method to update/call
        attribute = components[-1]
        if hasattr(target, attribute):
            attr = getattr(target, attribute)
            if isinstance(attr, property):
                # If it's a property, update it
                setattr(target, attribute, value)
                logger.info(f"Successfully updated '{attribute}' to '{value}'.")
            elif callable(attr):
                # If it's a method, call it
                attr()  # Call the method with no arguments
                logger.info(f"Successfully called method '{attribute}'.")
            else:
                logger.error(f"Attribute '{attribute}' is not callable.")
        else:
            logger.error(f"Attribute '{attribute}' not found on instance of '{target.__class__.__name__}'.")

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