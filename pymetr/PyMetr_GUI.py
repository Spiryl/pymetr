
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logging.getLogger('pyvisa').setLevel(logging.CRITICAL)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(name)s - %(message)s")

handler.setFormatter(formatter)
logger.addHandler(handler)

import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'
import sys
import numpy as np
import importlib.util
import random
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui
from pyqtgraph.parametertree import Parameter, ParameterTree
from pymetr.factories import InstrumentFactory
from pymetr.instrument import Instrument
from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QDockWidget, QPushButton
from PySide6.QtWidgets import QWidget, QMainWindow, QFileDialog, QComboBox, QSizePolicy
from contextlib import contextmanager

factory = InstrumentFactory()

@contextmanager
def block_signals(objects):
    original_states = [obj.blockSignals(True) for obj in objects]
    yield
    for obj, state in zip(objects, original_states):
        obj.blockSignals(state)
            
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
        self.parameterTree.setAlternatingRowColors(True)
        self.parameterTree.setParameters(parameters, showTop=True)
        # if self.on_tree_state_changed:
        #     self.parameters.sigTreeStateChanged.connect(self.on_tree_state_changed)

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

                # We need to keep a map between parameters and properties
                parameter_path_map = self.extract_parameter_paths(self.parameter_tree_dict)
                logger.debug(f"Parameter path map for {unique_id}: {parameter_path_map}")

                # logger.debug(f"Building parameters parameter tree dictionary:\n {self.parameter_tree_dict}.")
                parameters = Parameter.create(name='params', type='group', children=self.parameter_tree_dict)

                # Build a new dock for the instrument and load the parameters in to the parameter tree
                parameter_dock = InstrumentParameterDock(unique_id, self, on_tree_state_changed=self.create_parameter_change_handler(unique_id))
                parameter_dock.setup_parameters(parameters)

                fetchDataThread = TraceDataFetcherThread(instr)

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

                # Connect the tree signals to the properties.
                parameters.sigTreeStateChanged.connect(self.create_parameter_change_handler(unique_id))

                # Start the fetch data thread.
                instr.trace_data_ready.connect(self.update_plot)
                fetchDataThread.trace_data_ready.connect(lambda data: self.on_trace_data_ready(data, unique_id))
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
    
    def construct_full_param_path(self, param):
        path_parts = []
        while param is not None:
            path_parts.insert(0, param.name())
            param = param.parent()
        return '.'.join(path_parts)

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
            if param.opts.get('type') in ['action','group']: 
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
            for param, change, data in changes:
                param_name = param.name()
                logger.debug(f"Parameter changed: {param_name}, Change: {change}, Data: {data}")

                # Check if the parameter type is 'action' to handle method execution
                if param.opts.get('type') == 'action':
                    if change == 'activated':  # Ensure the change type is an action activation
                        logger.debug(f"Action parameter activated: {param_name}")
                        # Dynamically find and call the associated method on the instrument
                        if hasattr(self.instruments[unique_id]['instance'], param_name):
                            method = getattr(self.instruments[unique_id]['instance'], param_name)
                            method()  # Execute the method
                            logger.debug(f"Executed action method: {param_name}")
                        else:
                            logger.error(f"No method found for action parameter: {param_name}")
                else:
                    # For non-action parameters, handle them as usual
                    full_param_path = self.construct_full_param_path(param).lstrip("params.")  # Normalize the parameter path
                    logger.debug(f"Constructed full parameter path: {full_param_path}")

                    parameter_path_map = self.instruments[unique_id]['parameter_path_map']
                    property_path = parameter_path_map.get(full_param_path)
                    logger.debug(f"Property path from map: {property_path}")

                    if property_path:
                        # Use existing logic to update the property based on its path
                        self.navigate_and_update_property(property_path, data, unique_id)
                    else:
                        logger.error(f"Property path missing for parameter: {param_name}")
        return parameter_changed

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
        logger.debug(f"Navigating path '{path}' to update value '{value}' in instrument {unique_id}")

        try:
            for i, comp in enumerate(components[:-1]):  # Navigate to the last but one component
                if '[' in comp and ']' in comp:  # Indexed access
                    base, index = comp.split('[')
                    index = int(index[:-1])  # Convert index to integer
                    # Adjust for Python's 0-based indexing if needed
                    index -= 1  # Subtract if necessary
                    target = getattr(target, base)[index]  # Navigate to indexed attribute
                else:
                    target = getattr(target, comp)  # Regular attribute access

            # Set the new value on the final property
            final_attr = components[-1]
            setattr(target, final_attr, value)
            logger.info(f"✅ Updated '{path}' to '{value}' in instrument {unique_id}")
        except Exception as e:
            logger.error(f"🚨 Failed to navigate or update '{path}' with '{value}': {e}")

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