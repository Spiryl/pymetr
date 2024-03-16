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
from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QDockWidget, QPushButton
from PySide6.QtWidgets import QWidget, QMainWindow, QFileDialog, QComboBox, QTextEdit, QSizePolicy

logger = logging.getLogger(__name__)

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
        self.setAllowedAreas(QtCore.Qt.RightDockWidgetArea)

        self.dockLayout = QVBoxLayout()
        self.dockWidget = QWidget()
        self.dockWidget.setLayout(self.dockLayout)

        # Add Instrument Button
        self.addInstrumentButton = QPushButton("Add Instrument")
        self.addInstrumentButton.clicked.connect(parent.add_instrument_button_clicked)
        self.dockLayout.addWidget(self.addInstrumentButton)

        # Log Level ComboBox
        self.logLevelComboBox = QComboBox()
        self.logLevelComboBox.addItems(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'NONE'])
        self.logLevelComboBox.currentTextChanged.connect(parent.change_log_level)
        self.dockLayout.addWidget(self.logLevelComboBox)

        self.setWidget(self.dockWidget)

        # Adjust the dock's appearance
        self.dockLayout.addStretch()
        self.dockWidget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

class InstrumentSelectionDialog(QDialog):
    """
    Dialog for selecting an instrument from a list of available instruments.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select an Instrument")
        self.setGeometry(100, 100, 500, 500)
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

        self.plotWidget = pg.PlotWidget() 
        self.setCentralWidget(self.plotWidget)  
        
        self.centralControlDock = CentralControlDock(self) 
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.centralControlDock)

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
                # Build the instrument model instance and open it up.
                instr = instr_class(selected_resource)
                instr.open()

                # Look for a driver based on model number and identify and then sync the settings
                parameters = factory.create_parameters_from_driver(_driver, instr)
                self.sync_parameters_with_instrument(parameters, instr)

                # Build a new dock for the instrument and load the parameters in to the parameter tree
                parameter_dock = InstrumentParameterDock(unique_id, self, on_tree_state_changed=self.create_parameter_change_handler(unique_id))
                parameter_dock.setup_parameters(parameters)

                # Add it to the Captain's log.
                self.instruments[unique_id]['dock'] = parameter_dock
                self.instruments[unique_id]['instance'] = instr
                self.instruments[unique_id]['parameters'] = parameters

                # Send it home!
                self.addDockWidget(QtCore.Qt.RightDockWidgetArea, parameter_dock)
                
            except Exception as e:
                logger.error(f"Failed to initialize instrument {unique_id}: {e}")
        else:
            logger.error("Driver module for {unique_id} does not support instance creation.")

    def sync_parameters_with_instrument(self, parameters, instrument_instance):
        """
        Sync the Parameter Tree with the current state of the instrument by fetching the
        current values of the instrument's properties and updating the Parameter Tree.
        """
        def update_param_value(param, instr):
            property_path = param.opts.get('property_path', None)
            logger.debug(f"Syncing parameter: {param.name()} using property path: {property_path}")
            
            if property_path:
                parts = property_path.split('.')
                target = instr
                # Navigate through the instrument and its subsystems based on the property path
                for part in parts[:-1]:
                    logger.debug(f"Checking for subsystem or property: {part} in {target}")
                    if hasattr(target, part):
                        target = getattr(target, part)
                        logger.debug(f"Accessing: {part}")
                    else:
                        logger.error(f"Path '{property_path}' not valid: '{part}' not found")
                        return
                
                # Set the final property value
                property_name = parts[-1]
                if hasattr(target, property_name):
                    current_value = getattr(target, property_name)
                    param.setValue(current_value)
                    logger.debug(f"Parameter '{property_name}' set to '{current_value}'")
                else:
                    logger.error(f"Property '{property_name}' not found in {target}")
            else:
                logger.warning(f"No property path for parameter '{param.name()}'")

        # Iterate over all parameters in the tree and update their values
        for child in parameters.children():
            update_param_value(child, instrument_instance)
            # Recurse into groups if they exist
            if child.hasChildren():
                for subchild in child.children():
                    update_param_value(subchild, instrument_instance)

    def get_property_name_from_param(self, param):
        """
        Derives the property name from a Parameter.

        Args:
            param (Parameter): The parameter from which to derive the property name.

        Returns:
            str: The derived property name, or None if not applicable.
        """
        # Example implementation, to be adjusted based on actual parameter structure
        return param.opts.get('property_path', None).split('.')[-1] if 'property_path' in param.opts else None

    def create_parameter_change_handler(self, unique_id):
        """
        Creates a closure that captures the unique identifier of an instrument and
        returns a function that is triggered upon parameter changes in the GUI.

        The returned function serves as a bridge, funneling GUI changes through to
        the instrument's properties, ensuring the instrument's state reflects the
        user's input.

        Args:
            unique_id (str): The unique identifier for the instrument.

        Returns:
            function: A handler function that takes parameter changes and applies them to the instrument.
        """
        def parameter_changed(param, changes):
            """
            Handles parameter changes by dispatching them to the appropriate method
            to reflect these changes on the instrument.

            This function is connected to the signal emitted by the parameter tree
            whenever a user modifies a parameter's value.

            Args:
                param (Parameter): The parameter that was changed.
                changes (list): A list of changes, each being a tuple (param, change, data).
                unique_id (str): Captured unique identifier for the instrument.
            """
            self.on_tree_state_changed(param, changes, unique_id)
        return parameter_changed

    def on_tree_state_changed(self, param, changes, unique_id):
        """
        Responds to signals indicating that a parameter's state has changed in the GUI,
        initiating the process to update the corresponding property in the instrument's
        driver.

        This method iterates over all signaled changes, translating them into property
        updates or method calls as necessary to synchronize the instrument's state
        with the GUI.

        Args:
            param (Parameter): The parameter that was changed.
            changes (list): A list of changes, each being a tuple (param, change, data).
            unique_id (str): The unique identifier for the instrument affected by the changes.
        """
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
        """
        Navigates the hierarchy of the instrument's properties based on the given path,
        then updates the property or calls the method at the path's end with the provided value.

        This method ensures that GUI changes are accurately reflected within the instrument's
        driver, maintaining synchronicity between the GUI and the instrument's actual state.

        Args:
            path (str): The dot-separated path leading to the property or method to be updated.
            value: The new value to set for the property, or the value to use in the method call.
            unique_id (str): The unique identifier for the instrument.
        """
        components = path.split('.')
        target = self.instruments[unique_id]['instance']

        for comp in components[:-1]:
            comp = comp.lower()  # Ensure we're navigating correctly
            target = getattr(target, comp, None)
            if target is None:
                logger.error(f"Component '{comp}' not found in path '{path}'. Stopping navigation.")
                return

        property_name = components[-1]
        if hasattr(target, property_name):
            attr = getattr(target.__class__, property_name, None)
            if isinstance(attr, property):
                setattr(target, property_name, value)
                logger.info(f"Successfully updated '{property_name}' to '{value}'.")
            else:
                logger.error(f"Attribute '{property_name}' not a property or not found.")
        else:
            logger.error(f"Attribute '{property_name}' not found on instance of '{target.__class__.__name__}'.")

    def change_log_level(self, level):
        numeric_level = getattr(logging, level, None)
        if isinstance(numeric_level, int):
            logging.basicConfig(level=numeric_level)
            logger.setLevel(numeric_level)
            logger.info(f"Log level changed to {level}")
        else:
            logger.error(f"Invalid log level: {level}")

    def toggle_logging_dock(self):
        if self.loggingDock.isVisible():
            self.loggingDock.hide()
        else:
            self.loggingDock.show()

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