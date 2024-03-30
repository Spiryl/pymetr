# pymetr/application/instrument_factory.py
import logging
logger = logging.getLogger(__name__)

import ast
from pymetr.application.instrument_visitor import InstrumentVisitor
from pymetr import SelectProperty, StringProperty, ValueProperty, DataProperty, SwitchProperty

class InstrumentFactory:
    def __init__(self):
        self.current_instrument = None

    def create_instrument_data_from_driver(self, path):
        logger.debug(f"Creating instrument data from driver: {path}")
        instrument_data = self.parse_source_file(path)
        parameter_tree_dict = self.generate_parameter_tree_dict(instrument_data)
        methods_dict = self.generate_methods_dict(instrument_data)
        sources_list = self.generate_sources_list(instrument_data)
        return {
            'parameter_tree': parameter_tree_dict,
            'methods': methods_dict,
            'sources': sources_list
        }

    def set_current_instrument(self, instrument):
        self.current_instrument = instrument
        logger.debug(f"Current instrument set to: {self.current_instrument}")

    def parse_source_file(self, path):
        logger.debug(f"Initiating parse of source file: {path}")
        with open(path, 'r') as file:
            source = file.read()
        tree = ast.parse(source, filename=path)
        visitor = InstrumentVisitor()
        visitor.visit(tree)
        logger.debug(f"Completed parsing. Extracted instruments: {list(visitor.instruments.keys())}")
        return visitor.instruments

    def generate_methods_dict(self, instrument_data):
        """
        Generates a dictionary of methods for each instrument class.
        Args:
            instrument_data (dict): Instrument data, including methods.
        Returns:
            dict: A dictionary of methods, keyed by method name.
        """
        logger.info("📂 Starting to generate the methods dictionary... 📂")
        methods_dict = {}
        for class_name, class_info in instrument_data.items():
            logger.info(f"🔍 Processing Instrument: {class_name} 🔍")
            for method_name in class_info.get('methods', []):
                logger.info(f"🔧 Adding method: {method_name} 🔧")
                methods_dict[method_name] = getattr(self.current_instrument, method_name)
        logger.info("✅ Finished generating the methods dictionary ✅")
        return methods_dict

    def generate_properties_list(self, properties, class_name, subsystem=None):
        """
        Generates a list of property dictionaries for a given set of properties, class name, and optional subsystem.
        """
        properties_list = []
        for prop in properties:
            param_dict = self.construct_param_dict(prop, class_name, subsystem=subsystem)
            properties_list.append(param_dict)
            logger.debug(f"Property added: {prop['name']} for {class_name}")
        logger.debug("Properties list prepared.")
        return properties_list

    def generate_sources_list(self, instrument_data):
        """
        Generates a list of sources for the instrument.
        Args:
            instrument_data (dict): Instrument data, including sources.
        Returns:
            list: A list of sources for the instrument.
        """
        logger.info("🔍 Generating sources list... 🔍")
        for class_name, class_info in instrument_data.items():
            if 'sources' in class_info:
                logger.info(f"✅ Sources found for {class_name}: {class_info['sources']} ✅")
                return class_info['sources']
        logger.warning("⚠️ No sources found in the instrument data ⚠️")
        return []

    def construct_param_dict(self, prop, class_name, index=None, subsystem=None):
        logger.debug(f"🚀 Starting construct_param_dict for '{prop['name']}' in '{class_name}' 🚀")

        # Construct the property path considering indexing and nested subsystems
        logger.debug(f"🔍 Checking if '{prop['name']}' needs indexing... 🔍")
        property_path = f"{class_name.lower()}"
        if subsystem:
            property_path += f".{subsystem.lower()}"
        if index is not None:
            logger.debug(f"📊 Index provided. Appending to property path: [{index}] 📊")
            property_path += f"[{index}]"
        property_path += f".{prop['name']}"
        logger.debug(f"✅ Property path constructed: {property_path} ✅")

        # Initialize the param_dict
        logger.debug(f"📝 Initializing parameter dictionary for '{prop['name']}'... 📝")
        param_dict = {
            'name': prop['name'],
            'type': type(prop).__name__.lower(),
            'property_path': property_path,
            'value': None  # Default values can be set more intelligently based on the type or other metadata
        }

        logger.debug(f"🔧 Mapping property type '{prop['type']}' to parameter configuration... 🔧")
        if prop['type'] == 'SelectProperty':
            param_dict.update({
                'type': 'list',
                'limits': prop['choices'],
                'value': prop['choices'][0]  # Default to the first choice
            })
            logger.debug(f"📋 Updated for SelectProperty: {param_dict} 📋")
        elif prop['type'] == 'ValueProperty':
            param_dict.update({
                'type': 'float' if prop.get('value_type', 'float') == 'float' else 'int',
                'limits': prop.get('range', (None, None)),
                'value': 0.0 if prop.get('value_type', 'float') == 'float' else 0  # Default to 0.0 for floats, 0 for ints
            })
            logger.debug(f"📐 Updated for ValueProperty: {param_dict} 📐")
        elif prop['type'] == 'SwitchProperty':
            param_dict.update({
                'type': 'bool',
                'value': False  # Default to False
            })
            logger.debug(f"🔲 Updated for SwitchProperty: {param_dict} 🔲")
        elif prop['type'] == 'StringProperty':
            # Handle StringProperty as needed
            logger.debug(f"🔤 Handling StringProperty: {param_dict} 🔤")
        elif prop['type'] == 'DataProperty':
            # Handle DataProperty as needed
            logger.debug(f"⚙️ Handling DataProperty: {param_dict} ⚙️")

    def generate_parameter_tree_dict(self, instrument_data):
        """
        Generates a parameter tree dictionary from the instrument data, including subsystems and their properties.
        
        Args:
            instrument_data (dict): Instrument data, including subsystems and their properties.
        
        Returns:
            list: A parameter tree structure as a list of dictionaries.
        """
        logger.debug("🌳 Starting to generate the parameter tree... 🌳")
        tree_dict = []

        for class_name, class_info in instrument_data.items():
            logger.debug(f"🔍 Processing class: {class_name} 🔍")
            class_group = {
                'name': class_name,
                'type': 'group',
                'children': []
            }

            # Add the sources group
            sources_group = {
                'name': 'Sources',
                'type': 'group',
                'children': []
            }

            # Populate the sources group with checkboxes
            sources_list = class_info.get('sources', [])
            for source in sources_list:
                source_param = {
                    'name': source,
                    'type': 'bool',
                    'value': False  # Set the initial value to False (unchecked)
                }
                sources_group['children'].append(source_param)

            class_group['children'].append(sources_group)

            # Add the subsystem properties to the dictionary
            for subsystem_name, subsystem_info in class_info.get('subsystems', {}).items():
                logger.debug(f"🛠 Creating subsystem group: {subsystem_name} 🛠")
                subsystem_group = self.create_subsystem_group(subsystem_name, subsystem_info)
                class_group['children'].append(subsystem_group)

            tree_dict.append(class_group)
            logger.debug(f"🌲 Added class group: {class_name} to the tree 🌲")

        logger.debug(f"🚀 Generated parameter tree dictionary: {tree_dict} 🚀")
        logger.debug("🏁 Finished generating the parameter tree 🏁")
        return tree_dict

    def create_subsystem_group(self, subsystem_name, subsystem_info):
        """
        Creates a parameter group for a subsystem, adding logging and emoji flair for debug and clarity.
        Handles indexed instances if present, creating a group for each instance.

        Args:
            subsystem_name (str): The name of the subsystem.
            subsystem_info (dict): Info about the subsystem, including properties and instances.
        
        Returns:
            dict: A parameter group for the subsystem.
        """
        logger.debug(f"🔧 Starting to create subsystem group for: {subsystem_name} 🔧")
        if subsystem_info.get('needs_indexing', False):
            logger.debug(f"⚙️ {subsystem_name} requires indexing ⚙️")
            parent_group = {
                'name': subsystem_name,
                'type': 'group',
                'children': []
            }

            for index, instance_info in subsystem_info['instances'].items():
                logger.debug(f"📑 Creating indexed group for {subsystem_name}{index} 📑")
                indexed_group = {
                    'name': f"{subsystem_name}{index}",
                    'type': 'group',
                    'children': self.generate_properties_list(instance_info['properties'], f"{subsystem_name}[{index}]")
                }
                parent_group['children'].append(indexed_group)
                logger.debug(f"📚 Added indexed group for {subsystem_name}{index} 📚")
            
            logger.debug(f"📂 Completed indexed groups for {subsystem_name} 📂")
            logger.debug(f"✨ Final parent group for {subsystem_name}: {parent_group} ✨")
            return parent_group
        else:
            logger.debug(f"🗂 Creating group for non-indexed subsystem: {subsystem_name} 🗂")
            group = {
                'name': subsystem_name,
                'type': 'group',
                'children': self.generate_properties_list(subsystem_info['properties'], f"{subsystem_name}")
            }
            logger.debug(f"✨ Finished creating group for non-indexed subsystem: {subsystem_name} ✨")
            logger.debug(f"✨ Final group for {subsystem_name}: {group} ✨")
            return group