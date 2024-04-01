#  pymetr/gui/instrument_dock.py
import logging
logger = logging.getLogger()
import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'

import importlib.util
from pyqtgraph.parametertree import Parameter, ParameterTree

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QVBoxLayout, QDockWidget, QPushButton, QWidget, QFileDialog 

from pymetr.instrument import Instrument
from pymetr.application.instrument_factory import InstrumentFactory
from pymetr.application.trace_data_fetcher_thread import TraceDataFetcherThread

factory = InstrumentFactory()

class InstrumentDock(QDockWidget):
    """
    Dock widget to display and control the parameters of a connected instrument.
    """
    instrument_connected = Signal(str)  # Signal emitted when an instrument is successfully connected
    instrument_disconnected = Signal(str)  # Signal emitted when an instrument is disconnected
    trace_data_ready = Signal(object, str)  # Signal emitted when trace data is ready for plotting

    def __init__(self, parent=None):
        """
        Initializes the instrument dock.
        """
        logger.info(f"Creating instrument dock")
        super(InstrumentDock, self).__init__(parent)
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.setWidget(self.widget)
        self.instruments = {}  # Dictionary to store connected instruments

    def load_instrument_driver(self, _driver):
        """
        Loads the instrument driver from the given _driver.
        """
        module_name = os.path.splitext(os.path.basename(_driver))[0]
        logger.debug(f"Module name: {module_name}")
        spec = importlib.util.spec_from_file_location(module_name, _driver)
        logger.debug(f"Spec: {spec}")
        module = importlib.util.module_from_spec(spec)
        logger.debug(f"Module before exec_module: {module}")
        try:
            spec.loader.exec_module(module)
            logger.debug(f"Module after exec_module: {module}")
            return module
        except Exception as e:
            logger.error(f"Error loading instrument driver '{_driver}': {e}")
            return None

    def setup_parameters(self, parameters):
        """
        Receives a parameter tree and displays it within the dock.
        """
        logger.info(f"Setting up parameters")
        self.parameters = parameters
        self.parameterTree = ParameterTree()
        self.layout.addWidget(self.parameterTree)
        self.parameterTree.setAlternatingRowColors(False)
        self.parameterTree.setParameters(parameters, showTop=True)

    def add_action_button(self, button_text, handler_function):
        """
        Adds an action button to the instrument dock.

        Args:
            button_text (str): The text to display on the button.
            handler_function (callable): The function to be called when the button is clicked.
        """
        logger.info(f"Adding action button: {button_text}")
        button = QPushButton(button_text)
        button.clicked.connect(lambda: handler_function())
        self.layout.addWidget(button)

    def setup_instrument(self, selected_resource):
        """
        Engages with the selected instrument by loading its driver,
        opening a connection, and setting up its parameters in the UI.
        """
        logger.info(f"Setting up instrument")
        selected_key = [key for key, value in Instrument.list_instruments("TCPIP?*::INSTR")[0].items() if value == selected_resource][0]
        idn_response = selected_key.split(": ")[1]
        model_number = idn_response.split(',')[1].strip().upper()
        serial_number = idn_response.split(',')[2].strip()
        unique_id = f"{model_number}_{serial_number}"

        logger.info(f"Selected_key: {selected_key}")
        logger.info(f"IDN String: {idn_response}")
        logger.info(f"Model Number: {model_number}")
        logger.info(f"Serial Number: {serial_number}")
        logger.info(f"Unique Id: {unique_id}")

        # Initialize instrument record in the dictionary
        self.instruments[unique_id] = {
            'model_number': model_number,
            'serial_number': serial_number,
            # Placeholder for additional details to be added later
        }

        _driver = f"pymetr/instruments/{model_number.lower()}.py"
        logger.info(f"Looking for driver: {_driver}")
        if not os.path.exists(_driver):
            logger.info(f"No driver found for model {model_number}. Please select a driver file.")
            _driver, _ = QFileDialog.getOpenFileName(self, "Select Instrument Model File", "", "Python Files (*.py)")

        if _driver:
            logger.info(f"Loading driver: {_driver}")
            module = self.load_instrument_driver(_driver)
            logger.info(f"Returned module: {module}")
            if module:
                self.initialize_instrument(module, selected_resource, unique_id, _driver)

    def initialize_instrument(self, module, selected_resource, unique_id, _driver):
        instr_class = self.get_instrument_class_from_module(module)
        if not instr_class:
            logger.error(f"Driver module for {unique_id} does not support instance creation.")
            return

        instr = self.create_instrument_instance(instr_class, selected_resource, unique_id)
        if not instr:
            return

        factory = InstrumentFactory()
        instrument_data = factory.create_instrument_data_from_driver(_driver)

        self.setup_parameter_tree(instrument_data, unique_id)
        self.setup_method_buttons(instrument_data['methods'], instr)  # Pass the instrument instance to setup_method_buttons
        self.setup_sources_group(instrument_data['sources'])

        self.instruments[unique_id] = {
            'instance': instr,
            'parameters': self.parameters,
            'fetch_thread': self.create_fetch_thread(instr),
            'parameter_path_map': self.parameter_path_map,
            'methods': instrument_data['methods'],
            'sources': instrument_data['sources']
        }
        logger.info(f"Instrument {unique_id} added to the tracking dictionary.")

        self.synchronize_instrument(unique_id)
        self.connect_signals_and_slots(unique_id)
        self.start_fetch_thread(unique_id)
        self.instrument_connected.emit(unique_id)

    def get_instrument_class_from_module(self, module):
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Instrument) and attr != Instrument:
                logger.info(f"Instrument class found: {attr.__name__}")
                return attr
        return None

    def create_instrument_instance(self, instr_class, selected_resource, unique_id):
        try:
            instr = instr_class(selected_resource)
            logger.info(f"Instrument instance created: {instr}")
            instr.open()
            logger.info(f"Instrument {unique_id} connection opened.")
            return instr
        except Exception as e:
            logger.error(f"Failed to create instrument instance for {unique_id}: {e}")
            return None

    def setup_parameter_tree(self, instrument_data, unique_id):
        self.parameters_dict = instrument_data['parameter_tree']
        self.parameter_path_map = self.extract_parameter_paths(self.parameters_dict)
        logger.info(f"Parameter path map for {unique_id}: {self.parameter_path_map}")
        self.parameters = Parameter.create(name='params', type='group', children=self.parameters_dict)
        self.setup_parameters(self.parameters)

    def setup_method_buttons(self, method_names, instr):
        for method_name in method_names:
            if method_name in ['fetch_trace']:
                method_func = getattr(instr, method_name)  # Get the actual method from the instrument instance
                self.add_action_button(method_name, method_func)

    def setup_sources_group(self, sources_list):
        sources_group = {
            'name': 'Sources',
            'type': 'group',
            'children': [{'name': source, 'type': 'bool', 'value': False} for source in sources_list]
        }
        self.parameters_dict.insert(0, sources_group)

    def create_fetch_thread(self, instr):
        return TraceDataFetcherThread(instr)

    def connect_signals_and_slots(self, unique_id):
        self.instruments[unique_id]['fetch_thread'].trace_data_ready.connect(lambda data: self.trace_data_ready.emit(data, unique_id))
        self.parameters.sigTreeStateChanged.connect(self.create_parameter_change_handler(unique_id))
        self.instruments[unique_id].source_changed.connect(self.instruments[unique_id].sources.set_active_sources)

    def start_fetch_thread(self, unique_id):
        self.instruments[unique_id]['fetch_thread'].start()

    def synchronize_instrument(self, unique_id):
        parameters = self.instruments[unique_id]['parameters']
        instrument_instance = self.instruments[unique_id]['instance']
        parameter_path_map = self.instruments[unique_id]['parameter_path_map']

        def update_param_value(param, instr, full_param_path):
            if param.opts.get('type') in ['action','group']: 
                logger.info(f"Skipping {param.opts.get('type')} parameter: {param.name()}")
                return

            property_path = parameter_path_map.get(full_param_path)
            if property_path:
                try:
                    # Fetch the property's current value via translate_property_path
                    # Note: translate_property_path is expected to return the property value directly
                    property_value = self.translate_property_path(instr, property_path)
                    logger.info(f"Updating parameter '{param.name()}' with value from path '{property_path}': {property_value}")

                    # Update the parameter's value in the parameter tree to reflect the instrument's current state
                    param.setValue(property_value)
                except Exception as e:
                    logger.error(f"Error resolving path '{property_path}' for parameter '{param.name()}': {e}")
            else:
                logger.warning(f"No property path for parameter '{param.name()}'")

        def traverse_and_sync(param_group, path_prefix=''):
            logger.info(f"Traversing into children of '{path_prefix.rstrip('.')}'")
            for param in param_group.children():
                full_param_path = f"{path_prefix}.{param.name()}" if path_prefix else param.name()
                logger.info(f"Processing parameter: {full_param_path}")
                update_param_value(param, instrument_instance, full_param_path)
                if param.hasChildren():
                    new_path_prefix = full_param_path
                    traverse_and_sync(param, new_path_prefix)

        # Start the traversal with the root parameters group
        traverse_and_sync(parameters)

    def update_instrument(self, path, value, unique_id):
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
        logger.info(f"Navigating path '{path}' to update value '{value}' in instrument {unique_id}")

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

    def extract_parameter_paths(self, tree_dict, path_map=None, parent_path=None):
        if path_map is None:
            path_map = {}
        for item in tree_dict:
            if 'name' not in item:
                logger.warning(f"Skipping item without 'name' key: {item}")
                continue
            current_path = f"{parent_path}.{item['name']}" if parent_path else item['name']
            if 'children' in item:
                logger.info(f"Traversing into children of '{current_path}'")
                self.extract_parameter_paths(item['children'], path_map, parent_path=current_path)
            elif 'property_path' in item:
                path_map[current_path] = item['property_path']
                logger.info(f"Mapping '{current_path}' to property path '{item['property_path']}'")
        return path_map
    
    def construct_parameter_path(self, param):
        path_parts = []
        while param is not None:
            path_parts.insert(0, param.name())
            param = param.parent()
        return '.'.join(path_parts)

    def translate_property_path(self, instr, path):
        parts = path.split('.')
        target = instr  # Starting point is the instrument
        logger.info(f"Starting translation of path '{path}' from instrument {instr}")

        for part in parts:
            logger.info(f"Processing part '{part}' of path")
            if '[' in part and ']' in part:  # Indexed access
                base, index = part.split('[')
                index = int(index[:-1])  # Convert index to integer, removing the closing bracket

                # Adjust for Python's 0-based indexing if needed
                index -= 1  # Subtract one here if your input is 1-based but the internal representation is 0-based

                if not hasattr(target, base):
                    logger.error(f"Attribute '{base}' not found in object {target}. Path: {path}")
                    raise AttributeError(f"Attribute '{base}' not found in object {target}. Path: {path}")

                target = getattr(target, base)
                logger.info(f"Found base '{base}', now accessing index {index}")
                if not isinstance(target, (list, tuple)):
                    logger.error(f"Attribute '{base}' is not indexable. Path: {path}")
                    raise TypeError(f"Attribute '{base}' is not indexable. Path: {path}")

                try:
                    target = target[index]
                    logger.info(f"Indexed access successful, moved to '{target}'")
                except IndexError:
                    logger.error(f"Index {index} out of bounds for '{base}'. Path: {path}")
                    raise IndexError(f"Index {index} out of bounds for '{base}'. Path: {path}")
            else:
                if not hasattr(target, part):
                    logger.error(f"Attribute '{part}' not found in object {target}. Path: {path}")
                    raise AttributeError(f"Attribute '{part}' not found in object {target}. Path: {path}")
                target = getattr(target, part)  # Regular attribute access
                logger.info(f"Moved to attribute '{part}', now at '{target}'")

        logger.info(f"Completed translation of path '{path}', final target: '{target}'")
        return target

    def create_parameter_change_handler(self, unique_id):
        def parameter_changed(param, changes):
            for param, change, data in changes:
                param_name = param.name()
                logger.info(f"Parameter changed: {param_name}, Change: {change}, Data: {data}")

                # Check if the parameter type is 'action' to handle method execution
                if param.opts.get('type') == 'action':
                    if change == 'activated':  # Ensure the change type is an action activation
                        logger.info(f"Action parameter activated: {param_name}")
                        # Dynamically find and call the associated method on the instrument
                        if hasattr(self.instruments[unique_id]['instance'], param_name):
                            method = getattr(self.instruments[unique_id]['instance'], param_name)
                            method()  # Execute the method
                            logger.info(f"Executed action method: {param_name}")
                        else:
                            logger.error(f"No method found for action parameter: {param_name}")
                            # Check if the parameter is in the "Sources" group
                elif param.parent() and param.parent().name() == "Sources":
                    logger.info(f"Source {param_name} changed to {data}")
                    # Handle the source checkbox state change here
                    if data:
                        self.instruments[unique_id].add_source(param_name, unique_id)
                    else:
                        self.instruments[unique_id].remove_source(param_name, unique_id)
                else:
                    # For non-action parameters, handle them as usual
                    full_param_path = self.construct_parameter_path(param).lstrip("params.")  # Normalize the parameter path
                    logger.info(f"Constructed full parameter path: {full_param_path}")

                    parameter_path_map = self.instruments[unique_id]['parameter_path_map']
                    property_path = parameter_path_map.get(full_param_path)
                    logger.info(f"Property path from map: {property_path}")

                    if property_path:
                        # Use existing logic to update the property based on its path
                        self.update_instrument(property_path, data, unique_id)
                    else:
                        logger.error(f"Property path missing for parameter: {param_name}")
        return parameter_changed
    
if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PyMetr import Instrument
    import sys
    app = QApplication(sys.argv)

    resource = Instrument.select_instrument("TCPIP?*::INSTR")
    dock = InstrumentDock()
    dock.setup_instrument(resource)

    # Add any additional testing or debugging code here

    sys.exit(app.exec())