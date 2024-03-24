
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
            logger.debug(f"Inspecting attribute: {attr}, Name: {attr_name}")
            if isinstance(attr, type) and issubclass(attr, Instrument) and attr != Instrument:
                instr_class = attr
                logger.debug(f"Instrument class found: {instr_class.__name__}")
                break

        if instr_class:
            try:
                # Build the instrument model instance and open it up.
                instr = instr_class(selected_resource)
                logger.debug(f"Instrument instance created: {instr}")
                instr.open()
                logger.debug(f"Instrument {unique_id} connection opened.")

                # Set up the instrument control tree
                factory.set_current_instrument(instr)
                self.parameter_tree_dict = factory.create_parameters_from_driver(_driver)
                parameter_path_map = self.extract_parameter_paths(self.parameter_tree_dict)


                # logger.debug(f"Building parameters parameter tree dictionary:\n {self.parameter_tree_dict}.")
                parameters = Parameter.create(name='params', type='group', children=self.parameter_tree_dict)


                instr.trace_data_ready.connect(self.update_plot)

                # Build a new dock for the instrument and load the parameters in to the parameter tree
                parameter_dock = InstrumentParameterDock(unique_id, self, on_tree_state_changed=self.create_parameter_change_handler(unique_id))
                parameter_dock.setup_parameters(parameters)

                fetchDataThread = TraceDataFetcherThread(instr)
                fetchDataThread.trace_data_ready.connect(lambda data: self.on_trace_data_ready(data, unique_id))

                # Add it to the Captain's log.
                self.instruments[unique_id] = {
                    'dock': parameter_dock,
                    'instance': instr,
                    'parameters': parameters,
                    'plot_data_emitter': PlotDataEmitter(),
                    'fetch_thread': fetchDataThread,
                    'parameter_path_map': parameter_path_map
                }
                logger.debug(f"Instrument {unique_id} added to the tracking dictionary.")

                # See if we can sync it up
                self.sync_parameters_with_instrument(unique_id)

                # Connect signals to slots for plot updates.
                self.instruments[unique_id]['plot_data_emitter'].plot_data_ready.connect(self.on_trace_data_ready)
                logger.debug(f"Plot data ready signal connected for instrument {unique_id}.")

                # Add the instrument dock to the main window.
                self.addDockWidget(QtCore.Qt.RightDockWidgetArea, parameter_dock)
                logger.debug(f"Instrument dock added to main window for instrument {unique_id}.")

                # Start the fetch data thread
                fetchDataThread.start()

            except Exception as e:
                logger.error(f"Failed to initialize instrument {unique_id}: {e}")
        else:
            logger.error(f"Driver module for {unique_id} does not support instance creation.")

    def extract_parameter_paths(self, tree_dict, path_map=None, parent_path=None):
        if path_map is None:
            path_map = {}
        for item in tree_dict:
            current_path = f"{parent_path}.{item['name']}" if parent_path else item['name']
            if 'children' in item:
                logger.debug(f"Traversing into children of '{current_path}'")
                self.extract_parameter_paths(item['children'], path_map, parent_path=current_path)
            elif 'property_path' in item:
                path_map[current_path] = item['property_path']
                logger.debug(f"Mapping '{current_path}' to property path '{item['property_path']}'")
        return path_map

    # def translate_property_path(instr, path):
    #     parts = path.split('.')
    #     target = instr  # Starting point is the instrument

    #     for part in parts:
    #         if '[' in part and ']' in part:  # Indexed access
    #             base, index = part[:-1].split('[')
    #             target = getattr(target, base)  # Get the base attribute (the list)
    #             target = target[int(index)]  # Access the indexed element
    #         else:
    #             target = getattr(target, part)  # Regular attribute access

    #     return target
    
    def translate_property_path(self, instr, path):
        parts = path.split('.')
        target = instr  # Starting point is the instrument
        logger.debug(f"Starting translation of path '{path}' from instrument {instr}")

        for part in parts:
            logger.debug(f"Processing part '{part}' of path")
            if '[' in part and ']' in part:  # Indexed access
                base, index = part.split('[')
                index = int(index[:-1])  # Convert index to integer, removing the closing bracket

                # Adjust for Python's 0-based indexing if needed
                index -= 1  # Subtract one here if your input is 1-based but the internal representation is 0-based

                if not hasattr(target, base):
                    logger.error(f"Attribute '{base}' not found in object {target}. Path: {path}")
                    raise AttributeError(f"Attribute '{base}' not found in object {target}. Path: {path}")

                target = getattr(target, base)
                logger.debug(f"Found base '{base}', now accessing index {index}")
                if not isinstance(target, (list, tuple)):
                    logger.error(f"Attribute '{base}' is not indexable. Path: {path}")
                    raise TypeError(f"Attribute '{base}' is not indexable. Path: {path}")

                try:
                    target = target[index]
                    logger.debug(f"Indexed access successful, moved to '{target}'")
                except IndexError:
                    logger.error(f"Index {index} out of bounds for '{base}'. Path: {path}")
                    raise IndexError(f"Index {index} out of bounds for '{base}'. Path: {path}")
            else:
                if not hasattr(target, part):
                    logger.error(f"Attribute '{part}' not found in object {target}. Path: {path}")
                    raise AttributeError(f"Attribute '{part}' not found in object {target}. Path: {path}")
                target = getattr(target, part)  # Regular attribute access
                logger.debug(f"Moved to attribute '{part}', now at '{target}'")

        logger.debug(f"Completed translation of path '{path}', final target: '{target}'")
        return target

    def sync_parameters_with_instrument(self, unique_id):
        parameters = self.instruments[unique_id]['parameters']
        instrument_instance = self.instruments[unique_id]['instance']
        parameter_path_map = self.instruments[unique_id]['parameter_path_map']

        def update_param_value(param, instr, full_param_path):
            if param.opts.get('type') in ['action', 'group']:
                logger.debug(f"Skipping {param.opts.get('type')} parameter: {param.name()}")
                return

            property_path = parameter_path_map.get(full_param_path)
            if property_path:
                try:
                    # Fetch the property's current value via translate_property_path
                    # Note: translate_property_path is expected to return the property value directly
                    property_value = self.translate_property_path(instr, property_path)
                    logger.debug(f"Updating parameter '{param.name()}' with value from path '{property_path}': {property_value}")

                    # Update the parameter's value in the parameter tree to reflect the instrument's current state
                    param.setValue(property_value)
                except Exception as e:
                    logger.error(f"Error resolving path '{property_path}' for parameter '{param.name()}': {e}")
            else:
                logger.warning(f"No property path for parameter '{param.name()}'")

        def traverse_and_sync(param_group, path_prefix=''):
            logger.debug(f"Traversing into children of '{path_prefix.rstrip('.')}'")
            for param in param_group.children():
                full_param_path = f"{path_prefix}.{param.name()}" if path_prefix else param.name()
                logger.debug(f"Processing parameter: {full_param_path}")
                update_param_value(param, instrument_instance, full_param_path)
                if param.hasChildren():
                    new_path_prefix = full_param_path
                    traverse_and_sync(param, new_path_prefix)

        # Start the traversal with the root parameters group
        traverse_and_sync(parameters)

    def create_parameter_change_handler(self, unique_id):
        def parameter_changed(param, changes):
            parameter_path_map = self.instruments[unique_id]['parameter_path_map']
            for param, change, data in changes:
                param_name = param.name()  # Assuming this gives you the 'name' field of the parameter
                # Construct the path to this parameter to look it up in the map
                full_param_path = self.construct_full_param_path(param)
                property_path = parameter_path_map.get(full_param_path)
                if property_path:
                    self.navigate_and_update_property(property_path, data, unique_id)
                else:
                    logger.error(f"Property path missing for parameter: {param_name}")
        return parameter_changed

    def construct_full_param_path(self, param):
        path_parts = []
        while param is not None:
            path_parts.insert(0, param.name())
            param = param.parent()
        return '.'.join(path_parts)

    # def on_tree_state_changed(self, param, changes, unique_id):
    #     """
    #     Adjusts the process of handling parameter state changes from the GUI,
    #     ensuring property paths are accurately used for instrument updates.
    #     """
    #     logger.info(f"Tree changes detected for instrument {unique_id}.")
    #     for param, change, data in changes:
    #         _instrument = self.instruments[unique_id]

    #         # Retrieve the full property path from the parameter itself
    #         # Assuming each parameter holds its full property path as an attribute
    #         if hasattr(param, 'property_path'):
    #             property_path = getattr(param, 'property_path')
    #         else:
    #             logger.error(f"Property path missing for parameter: {param.name()}")
    #             continue  # Skip this change if property_path is not defined

    #         logger.debug(f"Parameter change - Path: {_instrument}{property_path}, Change: {change}, Data: {data}")
            
    #         # Use the correct property path to update the instrument
    #         self.navigate_and_update_property(property_path, data, unique_id)
    #         logger.info(f"Property '{property_path}' updated to '{data}'.")

    def navigate_and_update_property(self, path, value, unique_id):
        """
        Navigate through the instrument's properties/subsystems, including indexed ones,
        and update the target property with a new value.
        Args:
            path (str): The property path in dot-notation, supporting indexes (e.g., 'channel[1].probe').
            value: The new value to set at the target property.
            unique_id (str): Unique identifier for the instrument.
        """
        target = self.instruments[unique_id]['instance']
        components = path.split('.')

        try:
            for i, comp in enumerate(components[:-1]):  # Iterate through path components
                if '[' in comp and ']' in comp:  # Detect indexed access
                    base, index = comp[:-1].split('[')
                    index = int(index)
                    target = getattr(target, base)[index]  # Navigate to indexed attribute
                else:
                    target = getattr(target, comp)  # Regular attribute access

            # Update the final property
            final_attr = components[-1]
            if hasattr(target, final_attr):
                setattr(target, final_attr, value)
                logger.info(f"✅ '{path}' updated to '{value}' in {unique_id}.")
            else:
                logger.error(f"❌ Final property '{final_attr}' not found in path '{path}'. Update failed.")
        except Exception as e:
            logger.error(f"🚨 Failed navigating or updating '{path}' with '{value}': {e}")

    def on_trace_data_ready(self, plot_data, unique_id=None):
        if unique_id is not None:
            logger.debug(f"Plotting trace data for instrument: {unique_id}.")
        else:
            logger.debug("Plotting trace data.")
        self.update_plot(plot_data)

    def update_plot(self, data):
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
            logger.debug(f"Plotting trace dictionary {data}")
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