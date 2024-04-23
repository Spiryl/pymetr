# pymetr/application/instrument_factory.py
import logging
logger = logging.getLogger(__name__)
import json
import ast
from pymetr.application.instrument_visitor import InstrumentVisitor

class InstrumentFactory:
    def __init__(self):
        self.current_instrument = None

    def create_instrument_data_from_driver(self, path):
        logger.debug(f"Creating instrument data from driver: {path}")
        instrument_data = self.parse_source_file(path)
        
        parameter_tree_dict = self.generate_parameter_tree_dict(instrument_data)
        gui_methods_dict = self.generate_gui_methods_dict(instrument_data)
        other_methods_dict = self.generate_other_methods_dict(instrument_data)
        sources_list = self.generate_sources_list(instrument_data)
        return {
            'parameter_tree': parameter_tree_dict,
            'gui_methods': gui_methods_dict,
            'other_methods': other_methods_dict,
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

    def generate_gui_methods_dict(self, instrument_data):
        logger.info("📂 Starting to generate the GUI methods dictionary... 📂")
        gui_methods_dict = {}
        for class_name, class_info in instrument_data.items():
            logger.info(f"🔍 Processing Instrument: {class_name} 🔍")
            for method_name, method_info in class_info.get('gui_methods', {}).items():
                logger.info(f"🔧 Adding GUI method: {method_name} 🔧")
                gui_methods_dict[method_name] = method_info  # Store the method info dictionary
        logger.info("✅ Finished generating the GUI methods dictionary ✅")
        return gui_methods_dict

    def generate_other_methods_dict(self, instrument_data):
        logger.info("📂 Starting to generate the other methods dictionary... 📂")
        other_methods_dict = {}
        for class_name, class_info in instrument_data.items():
            logger.info(f"🔍 Processing Instrument: {class_name} 🔍")
            for method_name, method_info in class_info.get('other_methods', {}).items():
                logger.info(f"🔧 Adding other method: {method_name} 🔧")
                other_methods_dict[method_name] = method_info  # Store the method info dictionary
        logger.info("✅ Finished generating the other methods dictionary ✅")
        return other_methods_dict

    def generate_properties_list(self, properties, class_name, index=None, subsystem=None):
        logger.debug(f"🚀 Starting to generate properties list for class '{class_name}' with index '{index}'.")
        properties_list = []
        for prop in properties:
            logger.debug(f"🔍 Processing property '{prop['name']}' of type '{prop['type']}' for class '{class_name}'.")
            param_dict = self.construct_param_dict(prop, class_name, index, subsystem=subsystem)
            if param_dict is not None:
                properties_list.append(param_dict)
                logger.debug(f"✅ Added property '{prop['name']}' to properties list with path '{param_dict.get('property_path')}'.")
        
        logger.debug(f"🏁 Finished generating properties list for '{class_name}': Total properties {len(properties_list)}.")
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
        
        property_path = f"{class_name.lower()}"
        if subsystem and subsystem.lower() != class_name.lower():
            property_path += f".{subsystem.lower()}"
        if index is not None:
            logger.debug(f"📊 Index provided. Appending to property path: [{index}] 📊")
            property_path += f"[{index}]"
        property_path += f".{prop['name']}"
        logger.debug(f"✅ Property path constructed: {property_path} ✅")

        param_dict = {
            'name': prop['name'],
            'type': prop['type'].lower(),
            'property_path': property_path,
            'value': None,
            'readonly': prop.get('access', 'read-write') == 'read'  # Set readonly based on access
        }

        if prop['type'] == 'SelectProperty':
            param_dict.update({
                'type': 'list',
                'limits': prop['choices'],
                'value': prop['choices'][0]
            })
        elif prop['type'] == 'ValueProperty':
            param_dict.update({
                'type': prop.get('type', 'float'),
                'limits': prop.get('range', (None, None)),
                'value': 0.0,
                'units': prop.get('units', '')
            })
        elif prop['type'] == 'SwitchProperty':
            param_dict.update({
                'type': 'bool',
                'value': False
            })
        elif prop['type'] == 'StringProperty':
            param_dict.update({
                'type': 'str',
                'value': ''
            })
        elif prop['type'] == 'DataProperty':
            # Skip DataProperty for now
            return None

        logger.debug(f"✨ Constructed parameter dict for '{prop['name']}': {param_dict} ✨")
        return param_dict
    
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
                    'children': self.generate_properties_list(instance_info['properties'], subsystem_name, index=index)
                }
                parent_group['children'].append(indexed_group)
                logger.debug(f"📚 Added indexed group for {subsystem_name}{index} 📚")
            
            logger.debug(f"📂 Completed indexed groups for {subsystem_name} 📂")
            return parent_group
        else:
            logger.debug(f"🗂 Creating group for non-indexed subsystem: {subsystem_name} 🗂")
            group = {
                'name': subsystem_name,
                'type': 'group',
                'children': self.generate_properties_list(subsystem_info['properties'], subsystem_name)
            }
            logger.debug(f"✨ Finished creating group for non-indexed subsystem: {subsystem_name} ✨")
            return group
    
if __name__ == "__main__":

    factory = InstrumentFactory()

    # Load a test driver
    path = 'pymetr/instruments/dsox1204g.py'  
    with open(path, 'r') as file:
        source = file.read()

    instrument_data = factory.create_instrument_data_from_driver(path)

    print(json.dumps(instrument_data, indent=2))
    print(instrument_data)