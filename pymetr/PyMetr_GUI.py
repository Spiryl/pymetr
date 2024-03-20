
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logging.getLogger('pyvisa').setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(name)s - %(message)s")

handler.setFormatter(formatter)
logger.addHandler(handler)

import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'
import sys

import numpy as np
import importlib.util
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymetr.factories import InstrumentFactory
from pymetr.instrument import Instrument
from utilities.decorators import debug
from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QDockWidget, QPushButton
from PySide6.QtWidgets import QWidget, QMainWindow, QFileDialog, QComboBox, QSizePolicy

factory = InstrumentFactory()

class PlotDataEmitter(QObject):
    plot_data_ready = Signal(object)  # Emits plot data ready for plotting

class TraceDataFetcherThread(QThread):
    trace_data_ready = Signal(object)  # Emits when trace data is ready
    fetch_error = Signal(str)  # Emits in case of a fetching error

    def __init__(self, instrument):
        super(TraceDataFetcherThread, self).__init__()
        self.instrument = instrument

    def run(self):
        try:
            trace_data = self.instrument.fetch_trace()
            self.trace_data_ready.emit(trace_data)
        except Exception as e:
            self.fetch_error.emit(str(e))

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

class InstrumentParameterDock(QDockWidget):
    """
    Dock widget to display and control the parameters of a connected instrument.
    """
    def __init__(self, instrument, parent=None, on_tree_state_changed=None):
        """
        Initializes the parameter dock for a specific instrument.
        """
        logger.debug(f"Creating instrument parameter dock")
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
        logger.debug(f"Setting up parameters")
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
        logger.debug(f"Opening PyMetr Application")
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
        logger.debug(f"Add instrument button clicked")
        dialog = InstrumentSelectionDialog(self)
        if dialog.exec() == QDialog.Accepted:
            selected_resource = dialog.get_selected_instrument()
            self.setup_instrument(selected_resource)

    def setup_instrument(self, selected_resource):
        """
        Engages with the selected instrument by loading its driver,
        opening a connection, and setting up its parameters in the UI.
        """
        logger.debug(f"Setting up instrument")
        selected_key = [key for key, value in Instrument.list_instruments("TCPIP?*::INSTR")[0].items() if value == selected_resource][0]
        idn_response = selected_key.split(": ")[1]
        model_number = idn_response.split(',')[1].strip().upper()
        serial_number = idn_response.split(',')[2].strip()
        unique_id = f"{model_number}_{serial_number}"

        logger.debug(f"Selected_key: {selected_key}")
        logger.debug(f"IDN String: {idn_response}")
        logger.debug(f"Model Number: {model_number}")
        logger.debug(f"Serial Number: {serial_number}")
        logger.debug(f"Unique Id: {unique_id}")

        # Initialize instrument record in the dictionary
        self.instruments[unique_id] = {
            'model_number': model_number,
            'serial_number': serial_number,
            # Placeholder for additional details to be added later
        }

        _driver = f"pymetr/instruments/{model_number}.py"
        logger.debug(f"Looking for driver: {_driver}")
        if not os.path.exists(_driver):
            logger.info(f"No driver found for model {model_number}. Please select a driver file.")
            _driver, _ = QFileDialog.getOpenFileName(self, "Select Instrument Model File", "", "Python Files (*.py)")

        if _driver:
            logger.debug(f"Loading driver: {_driver}")
            module = self.load_instrument_driver(_driver)
            logger.debug(f"Returned module: {module}")
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
        logger.debug(f"Initializing instrument with module: {module}")

        # Identify the correct instrument class from the module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            logger.debug(f"Searching: {attr}, {attr_name}")
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
                instr.trace_data_ready.connect(self.update_plot)
                self.sync_parameters_with_instrument(parameters, instr)

                # Build a new dock for the instrument and load the parameters in to the parameter tree
                parameter_dock = InstrumentParameterDock(unique_id, self, on_tree_state_changed=self.create_parameter_change_handler(unique_id))
                parameter_dock.setup_parameters(parameters)

                fetchDataThread = TraceDataFetcherThread(instr)
                fetchDataThread.trace_data_ready.connect(lambda data: self.on_trace_data_ready(data, unique_id))
                fetchDataThread.fetch_error.connect(lambda error: self.onTraceFetchError(error, unique_id))
                fetchDataThread.start()

                # Add it to the Captain's log.
                self.instruments[unique_id] = {
                    'dock': parameter_dock,
                    'instance': instr,
                    'parameters': parameters,
                    'plot_data_emitter': PlotDataEmitter(),  # Updated key and value
                    'fetch_thread': fetchDataThread  # Keep the fetch thread reference
                }
                
                # Send out invitations to the plotting party.
                self.instruments[unique_id]['plot_data_emitter'].plot_data_ready.connect(self.on_trace_data_ready)
                
                # Send it home!
                self.addDockWidget(QtCore.Qt.RightDockWidgetArea, parameter_dock)
                
            except Exception as e:
                logger.error(f"Failed to initialize instrument {unique_id}: {e}")
        else:
            logger.error(f"Driver module for {unique_id} does not support instance creation.") 

    def sync_parameters_with_instrument(self, parameters, instrument_instance):
        """
        Sync the Parameter Tree with the current state of the instrument by fetching the
        current values of the instrument's properties and updating the Parameter Tree, ignoring action parameters.
        """
        def update_param_value(param, instr):
            # Skip action parameters as they don't represent a state to sync
            if param.opts.get('type') == 'action':
                logger.debug(f"Skipping action parameter: {param.name()}")
                return

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

    def on_trace_data_ready(self, plot_data, unique_id=None):
        if unique_id is not None:
            logger.debug(f"Plotting trace data for instrument: {unique_id}.")
        else:
            logger.debug("Plotting trace data.")
        self.update_plot(plot_data)

    def update_plot(self,data):
        """
        Updates the given plot_widget with the provided data.
        
        Parameters:
        - data: Can be a dictionary in the specified trace format, or other data formats compatible with pyqtgraph plotting functions (e.g., lists, np.arrays).
        - plot_widget: The PyQtGraph plotting widget to update.
        """
        
        plot_widget = self.plotWidget  # Access the plot widget from the instance
        plot_widget.clear()

        # Handle the trace_dictionary format
        if isinstance(data, dict):
            logger.info("Processing trace_dictionary format data for plotting.")
            for trace_id, trace_info in data.items():
                # Extract the necessary data for each trace
                trace_data = trace_info.get('data', [])
                trace_range = trace_info.get('range', np.arange(len(trace_data)))
                color = trace_info.get('color', 'w')  # Default color white
                label = trace_info.get('label', None)
                visible = trace_info.get('visible', True)  # Default visibility to True if not specified
                
                # Adjust color for visibility
                if not visible:
                    color = (0, 0, 0, 0)  # Set color to transparent for invisible traces
                    
                # Plotting the trace data with optional parameters
                logger.debug(f"Plotting trace ID {trace_id} with label: {label}, color: {color}, visible: {visible}.")
                plot_widget.plot(trace_range, trace_data, pen=color, name=label)

        # Direct plotting if data isn't in the expected dictionary format
        elif isinstance(data, (list, np.ndarray, tuple)):
            logger.info("Processing direct data format for plotting.")
            if isinstance(data, tuple):
                # If data comes as a tuple, unpack it assuming it follows the (data, range) format
                trace_data, trace_range = data
                logger.debug("Plotting tuple format data.")
                plot_widget.plot(trace_range, trace_data)
            else:
                # Directly plot the data if it's just a list or np.array
                logger.debug("Plotting list or np.array format data.")
                plot_widget.plot(data)
        else:
            # Log an error for unexpected data formats
            logger.error(f"Received data in an unexpected format, unable to plot: {data}")

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