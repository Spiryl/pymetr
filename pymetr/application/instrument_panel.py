#  pymetr/gui/instrument_dock.py
import logging
logger = logging.getLogger()
import os
os.environ['PYQTGRAPH_QT_LIB'] = 'PySide6'

import importlib.util
from pyqtgraph.parametertree import Parameter, ParameterTree
<<<<<<< Updated upstream

from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QVBoxLayout, QDockWidget, QPushButton, QWidget, QFileDialog 
=======
from PySide6.QtCore import Signal, Qt, Slot, QTimer
from PySide6.QtWidgets import QVBoxLayout, QDockWidget, QPushButton, QWidget, QApplication
>>>>>>> Stashed changes

from pymetr.core import Instrument
from pymetr.application.instrument_factory import InstrumentFactory

factory = InstrumentFactory()

class InstrumentManager(QObject):
    instrument_connected = Signal(str)
    trace_data_ready = Signal(object)
    parameter_updated = Signal(str, str, object)
    source_updated = Signal(str, str, bool) 

    def __init__(self):
        super().__init__()
        self.instruments = {}

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
        
    def get_instrument_class_from_module(self, module):
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Instrument) and attr != Instrument:
                logger.debug(f"Instrument class found: {attr.__name__}")
                return attr
        return None

    def create_instrument_instance(self, instr_class, selected_resource, unique_id):
        try:
            instr = instr_class(selected_resource)
            logger.debug(f"Instrument instance created: {instr}")
            instr.open()
            instr.reset()
            instr.query_operation_complete()
            logger.debug(f"Instrument {unique_id} connection opened.")
            self.instrument_connected.emit(unique_id)
            return instr
        except Exception as e:
            logger.error(f"Failed to create instrument instance for {unique_id}: {e}")
            return None
        
    def initialize_instrument(self, selected_resource):
        """
        Initializes the selected instrument by loading its driver and opening a connection.
        """
        logger.debug(f"Initializing instrument")
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

        _driver = f"pymetr/instruments/{model_number.lower()}.py"
        logger.debug(f"Looking for driver: {_driver}")
        if not os.path.exists(_driver):
            logger.debug(f"No driver found for model {model_number}. Please select a driver file.")
            _driver, _ = QFileDialog.getOpenFileName(self, "Select Instrument Model File", "", "Python Files (*.py)")

        if _driver:
            logger.debug(f"Loading driver: {_driver}")
            module = self.load_instrument_driver(_driver)
            logger.debug(f"Returned module: {module}")
            if module:
                return self.build_instrument(module, selected_resource, unique_id, _driver)
        
        return None

    def build_instrument(self, module, selected_resource, unique_id, _driver):
        instr_class = self.get_instrument_class_from_module(module)
        if not instr_class:
            logger.error(f"Driver module for {unique_id} does not support instance creation.")
            return None

        factory = InstrumentFactory()
        instrument_data = factory.create_instrument_data_from_driver(_driver)

        instr = self.create_instrument_instance(instr_class, selected_resource, unique_id)
        if not instr:
            return None
        
        self.parameters = Parameter.create(name=unique_id, type='group', children=instrument_data['parameter_tree'])

        self.instruments[unique_id] = {
            'instance': instr,
            'instr_data': instrument_data,
            'parameters': self.parameters,
            'methods': instrument_data['methods'],
            'sources': instrument_data['sources'],
            'path_map': self.extract_parameter_paths(instrument_data['parameter_tree']),
        }
        logger.debug(f"Instrument {unique_id} added to the tracking dictionary.")

        self.connect_signals_and_slots(unique_id)

        return self.instruments[unique_id], unique_id

    def update_sources(self, sources, unique_id):
        instr = self.instruments[unique_id]['instance']
        # Update the sources in the instrument
        instr.sources.source = sources
        # self.source_updated.emit(unique_id, sources) 

    def connect_signals_and_slots(self, unique_id):
        instr = self.instruments[unique_id]['instance']
        instr.trace_data_ready.connect(lambda data: self.trace_data_ready.emit(data))
        # instr.sources.source_changed.connect(lambda sources: self.update_sources(sources, unique_id))

    def synchronize_instrument(self, unique_id):
        parameters = self.instruments[unique_id]['parameters']
        instrument_instance = self.instruments[unique_id]['instance']
        path_map = self.instruments[unique_id]['path_map']

        def update_param_value(param, instr, full_param_path):
            if param.opts.get('type') in ['action','group']: 
                logger.debug(f"Skipping {param.opts.get('type')} parameter: {param.name()}")
                return

            property_path = path_map.get(full_param_path)
            if property_path:
                try:
                    # Note: translate_property_path is expected to return the property value directly
                    property_value = self.translate_property_path(instr, property_path)
                    self.parameter_updated.emit(unique_id, full_param_path, property_value)
                except Exception as e:
                    logger.error(f"Error resolving path '{property_path}' for parameter '{param.name()}': {e}")
            else:
                logger.warning(f"No property path for parameter '{param.name()}'")

        def traverse_and_sync(param_group, path_prefix=''):
            logger.debug(f"Traversing into children of '{path_prefix.rstrip('.')}'")
            logger.debug(f"Current active sources: {instrument_instance.sources.source}")
            for param in param_group.children():
                full_param_path = f"{path_prefix}.{param.name()}" if path_prefix else param.name()
                logger.debug(f"Processing parameter: {full_param_path}")

                # Check if the parameter is in the "Sources" group
                if param.parent() and param.parent().name() == "Sources":
                    # Synchronize the source checkbox state with the current sources.source value
                    source_name = param.name()
                    is_selected = source_name in instrument_instance.sources.source
                    logger.debug(f"Synchronizing source '{source_name}' to state: {is_selected}")
                    self.source_updated.emit(unique_id, source_name, is_selected)
                else:
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
            logger.debug(f"✅ Updated '{path}' to '{value}' in instrument {unique_id}")
        except Exception as e:
            logger.error(f"🚨 Failed to navigate or update '{path}' with '{value}': {e}")

    def construct_parameter_path(self, param):
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

    def extract_parameter_paths(self, tree_dict, path_map=None, parent_path=None):
        if path_map is None:
            path_map = {}

        for item in tree_dict:
            if 'name' not in item:
                logger.warning(f"Skipping item without 'name' key: {item}")
                continue

            current_path = f"{parent_path}.{item['name']}" if parent_path else item['name']

            if 'children' in item:
                logger.debug(f"Traversing into children of '{current_path}'")
                # Special handling for 'Sources' group
                if item.get('type') == 'group' and item['name'] == 'Sources':
                    for source_item in item['children']:
                        source_path = f"{current_path}.{source_item['name']}"
                        # Assuming there's a standard way to get the source state in your instrument class
                        property_path = f"sources.{source_item['name']}"
                        path_map[source_path] = property_path
                        logger.debug(f"Mapping source '{source_path}' to property path '{property_path}'")
                else:
                    self.extract_parameter_paths(item['children'], path_map, parent_path=current_path)
            elif 'property_path' in item:
                path_map[current_path] = item['property_path']
                logger.debug(f"Mapping '{current_path}' to property path '{item['property_path']}'")

        return path_map
    
class InstrumentPanel(QDockWidget):
    instrument_connected = Signal(str)
    instrument_disconnected = Signal(str)
    trace_data_ready = Signal(object)

    def __init__(self, instrument_manager, parent=None):
        super().__init__(parent)
        self.instrument_manager = instrument_manager
        self.instrument_manager.parameter_updated.connect(self.handle_parameter_update)
        self.instrument_manager.source_updated.connect(self.handle_source_update)
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.setWidget(self.widget)
        self.instruments = {}  # Dictionary to store connected instruments
        self.plot_mode = 'Single'
        self.colors = ['#5E57FF', '#4BFF36', '#F23CA6', '#FF9535']
        self.continuous_mode = False
        self.update_timer = QTimer()

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
        self.parameterTree.setDragEnabled(True)  # Enable drag functionality
        self.parameterTree.setAcceptDrops(True)  # Enable drop functionality

    def add_action_button(self, button_text, handler_function):
        """
        Adds an action button to the instrument dock.

        Args:
            button_text (str): The text to display on the button.
            handler_function (callable): The function to be called when the button is clicked.
        """
        logger.debug(f"Adding action button: {button_text}")
        button = QPushButton(button_text)
        button.clicked.connect(lambda: handler_function())
        self.layout.addWidget(button)

    def setup_parameter_tree(self, instrument, unique_id):
        instr_data = instrument['instr_data']
        self.parameters_dict = instr_data['parameter_tree']
        self.path_map = instrument['path_map']
        self.parameters = Parameter.create(name=unique_id, type='group', children=self.parameters_dict)
        self.setup_parameters(self.parameters)
        self.parameters.sigTreeStateChanged.connect(self.create_parameter_change_handler(unique_id))

        def update_param_attributes(param_dict):
            if 'access' in param_dict:
                param_dict['readonly'] = param_dict['access'] != 'write'
            if 'range' in param_dict:
                param_dict['limits'] = param_dict['range']
            if 'units' in param_dict:
                param_dict['units'] = param_dict['units']
            for child_dict in param_dict.get('children', []):
                update_param_attributes(child_dict)

        for param_dict in self.parameters_dict:
            update_param_attributes(param_dict)

    def setup_method_buttons(self, methods_dict, instr):
        for method_name, method_info in methods_dict.items():
            if method_info.get('is_source_method', False):
                method_func = getattr(instr, method_name)
                self.add_action_button(method_name, method_func)

    def setup_sources_group(self, sources_list):
        sources_group = {
            'name': 'Sources',
            'type': 'group',
            'children': [{'name': source, 'type': 'bool', 'value': False} for source in sources_list]
        }
        self.parameters_dict.insert(0, sources_group)

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
                        if hasattr(self.instrument_manager.instruments[unique_id]['instance'], param_name):
                            method = getattr(self.instrument_manager.instruments[unique_id]['instance'], param_name)
                            method()  # Execute the method
                            logger.debug(f"Executed action method: {param_name}")
                        else:
                            logger.error(f"No method found for action parameter: {param_name}")
                # Check if the parameter is in the "Sources" group
                elif param.parent() and param.parent().name() == "Sources":
                    logger.debug(f"Source {param_name} changed to {data}")
                    # Handle the source checkbox state change here
                    if data:
                        self.instrument_manager.instruments[unique_id]['instance'].sources.add_source(param_name)
                    else:
                        self.instrument_manager.instruments[unique_id]['instance'].sources.remove_source(param_name)
                else:
                    # For non-action parameters, handle them as usual
                    full_param_path = self.instrument_manager.construct_parameter_path(param).lstrip(unique_id)
                    full_param_path = full_param_path.lstrip(".")  
                    logger.debug(f"Constructed full parameter path: {full_param_path}")

                    path_map = self.instrument_manager.instruments[unique_id]['path_map']
                    property_path = path_map.get(full_param_path)
                    logger.debug(f"Property path from map: {property_path}")

                    if property_path:
                        # Use existing logic to update the property based on its path
                        self.instrument_manager.update_instrument(property_path, data, unique_id)
                    else:
                        logger.error(f"Property path missing for parameter: {param_name}")
        return parameter_changed

    def handle_parameter_update(self, unique_id, param_path, value):
        # Find and update the parameter in your parameter tree
        param = self.find_parameter_by_path(param_path)
        if param:
            param.setValue(value)

    def find_parameter_by_path(self, param_path):
        # Split path and find parameter based on path elements
        parts = param_path.split('.')
        current_params = self.parameters  # Assuming this is the root of your ParameterTree
        for part in parts:
            current_params = next((p for p in current_params.children() if p.name() == part), None)
            if current_params is None:
                return None
        return current_params
    
    def handle_source_update(self, unique_id, source_name, is_selected):
        # TODO: Fix Oscilloscope here. 
        source_param_path = f"Oscilloscope.Sources.{source_name}"
        param = self.find_parameter_by_path(source_param_path)
        if param:
            param.setValue(is_selected)
            logger.debug(f"Updated source '{source_name}' to state: {is_selected}")
        else:
            logger.error(f"Source parameter '{source_name}' not found in parameter tree")

    def setup_instrument_panel(self, instrument, unique_id):

        logger.debug(f"Setting up instrument panel for {unique_id}")
        self.unique_id = unique_id

        self.setup_method_buttons(instrument['methods'], instrument['instance'])
        self.setup_parameter_tree(instrument, unique_id)
        self.setup_sources_group(instrument['sources'])

        self.acquire_button = QPushButton("Acquire")
        self.acquire_button.clicked.connect(instrument['instance'].fetch_trace)  # Initially connect to fetch_trace
        logger.debug("Acquire button initially connected to fetch_trace")
        self.layout.addWidget(self.acquire_button)

        syncInstrumentButton = QPushButton(f"Sync {unique_id}")
        syncInstrumentButton.clicked.connect(lambda: self.instrument_manager.synchronize_instrument(unique_id))
        self.layout.addWidget(syncInstrumentButton)
        instrument['instance'].trace_data_ready.connect(self.on_trace_data_ready)

    def on_trace_data_ready(self, trace_data):
        logger.debug("Received trace data")
        QApplication.processEvents()
        self.trace_data_ready.emit(trace_data)  # Emit the trace_data_ready signal

    def toggle_acquisition(self, instrument_instance):
        logger.debug(f"Toggling acquisition for {self.unique_id}")
        self.continuous_mode = not self.continuous_mode
        logger.debug(f"Setting continuous mode to {self.continuous_mode} for instrument {instrument_instance}")
        instrument_instance.set_continuous_mode(self.continuous_mode)
        logger.debug(f"Emitting continuous_mode_changed signal with value {self.continuous_mode}")
        self.continuous_mode_changed.emit(self.continuous_mode)
        self.update_acquire_button(instrument_instance)
        if self.continuous_mode and self.plot_mode == 'Run':
            logger.debug(f"Starting continuous update timer")
            self.start_continuous_update_timer()
        else:
            logger.debug(f"Stopping continuous update timer")
            self.stop_continuous_update_timer()

    def start_continuous_update_timer(self):
        self.update_timer.start(100)  # Update the plot at 50 fps (1000 ms / 50 fps = 20 ms)

    def stop_continuous_update_timer(self):
        self.update_timer.stop()

    def emit_trace_data(self):
        instrument_instance = self.instrument_manager.instruments[self.unique_id]['instance']
        trace_data = instrument_instance.fetch_trace()
        self.trace_data_ready.emit(trace_data)

    def fetch_trace(self):
        logger.debug(f"Fetching trace for {self.unique_id}")
        instrument_instance = self.instrument_manager.instruments[self.unique_id]['instance']
        instrument_instance.fetch_trace()

    def update_acquire_button(self, instrument_instance):
        logger.debug(f"Updating acquire button for {self.unique_id}")
        if self.plot_mode == 'Run':
            logger.debug("Plot mode is 'Run'")
            self.acquire_button.setCheckable(True)
            self.acquire_button.setText("Stop" if self.continuous_mode else "Run")
            self.acquire_button.setStyleSheet(f"background-color: {self.colors[1 if instrument_instance.continuous_mode else 0]}")
            self.acquire_button.clicked.disconnect()  # Disconnect the previous signal
            logger.debug("Disconnected previous signal from acquire button")
            self.acquire_button.clicked.connect(lambda: self.toggle_acquisition(instrument_instance))
            logger.debug("Connected acquire button to toggle_acquisition")
        else:
            logger.debug("Plot mode is not 'Run'")
            self.acquire_button.setCheckable(False)
            self.acquire_button.setText("Acquire")
            self.acquire_button.setStyleSheet("")
            self.acquire_button.clicked.disconnect()  # Disconnect the previous signal
            logger.debug("Disconnected previous signal from acquire button")
            self.acquire_button.clicked.connect(instrument_instance.fetch_trace)
            logger.debug("Connected acquire button to fetch_trace")

    @Slot(str)
    def set_plot_mode(self, mode):
        logger.debug(f"Setting plot mode to {mode}")
        self.plot_mode = mode
        instrument_instance = self.instrument_manager.instruments[self.unique_id]['instance']
        self.update_acquire_button(instrument_instance)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication, QMainWindow
    from PyMetr import Instrument
    import sys

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Instrument Control")
            self.setGeometry(100, 100, 800, 600)

            self.instrument_manager = InstrumentManager()
            self.instrument_panel = None

            self.init_ui()

        def init_ui(self):
            resource = Instrument.select_instrument("TCPIP?*::INSTR")
            instrument, unique_id = self.instrument_manager.initialize_instrument(resource)
            if instrument:
                self.instrument_panel = InstrumentPanel(self.instrument_manager)
                self.instrument_panel.setup_instrument_panel(instrument, unique_id)
                self.addDockWidget(Qt.RightDockWidgetArea, self.instrument_panel)

    sys.argv += ['-platform', 'windows:darkmode=2']
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())