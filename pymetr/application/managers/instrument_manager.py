#  --- instrument_manager.py ---------
import os
import logging
logger = logging.getLogger()

import importlib.util
from pyqtgraph.parametertree import Parameter

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog 

from pymetr.core.instrument import Instrument
from pymetr.application.factories.instrument_factory import InstrumentFactory


class InstrumentManager(QObject):
    instrument_connected = Signal(str)
    trace_data_ready = Signal(object)
    parameter_updated = Signal(str, str, object)
    source_updated = Signal(str, str, bool) 

    def __init__(self):
        super().__init__()
        self.instruments = {}

    def load_instrument_driver(self, _driver):
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

        self.instruments[unique_id] = {
            'model_number': model_number,
            'serial_number': serial_number,
        }

        _driver = f"pymetr/drivers/{model_number.lower()}.py"
        logger.debug(f"Looking for driver: {_driver}")
        if not os.path.exists(_driver):
            logger.error(f"No driver found for model {model_number}.")
            return None

        logger.debug(f"Loading driver: {_driver}")
        module = self.load_instrument_driver(_driver)
        logger.debug(f"Returned module: {module}")
        if module:
            instrument = self.build_instrument(module, selected_resource, unique_id, _driver)
            return instrument, unique_id
        return None, None

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
            'gui_methods': instrument_data['gui_methods'],
            'sources': instrument_data['sources'],
            'path_map': self.extract_parameter_paths(instrument_data['parameter_tree']),
        }
        logger.debug(f"Instrument {unique_id} added to the tracking dictionary.")

        self.connect_signals_and_slots(unique_id)

        return self.instruments[unique_id], unique_id

    # TODO: handle this without expecting the instance name is sources
    # open to suggestions
    def update_sources(self, sources, unique_id):
        instr = self.instruments[unique_id]['instance']
        # Update the sources in the instrument
        instr.sources.source = sources

    def connect_signals_and_slots(self, unique_id):
        instr = self.instruments[unique_id]['instance']
        instr.trace_data_ready.connect(lambda data: self.trace_data_ready.emit(data))

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
    