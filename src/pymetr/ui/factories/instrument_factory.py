import json
import os
import ast
from pymetr.core.logging import logger
from ...drivers.base.visitor import InstrumentVisitor

class InstrumentFactory:
    def __init__(self):
        self.current_instrument = None

    def create_instrument_data_from_driver(self, path: str) -> dict:
        """
        Reads the driver source code from the given file path,
        extracts the raw instrument data model using the visitor,
        and then transforms that data model into a UI configuration.
        """
        logger.debug(f"Building UI configuration from driver source: {path}")
        with open(path, 'r') as file:
            source = file.read()
        return self.create_ui_configuration_from_source(source)

    def create_ui_configuration_from_source(self, source: str) -> dict:
        """
        Accepts driver source code as a string, builds the raw instrument data model,
        and converts it into a UI-friendly configuration.
        """
        visitor = InstrumentVisitor()
        # Build the raw data model from the source code.
        instrument_data_model = visitor.build_instrument_data_model(source)
        logger.debug(f"Raw instrument data model: {json.dumps(instrument_data_model, indent=2)}")
        
        # Convert the raw model into UI-friendly structures.
        parameter_tree_dict = self.generate_parameter_tree_dict(instrument_data_model)
        gui_methods_dict = self.generate_gui_methods_dict(instrument_data_model)
        other_methods_dict = self.generate_other_methods_dict(instrument_data_model)
        sources_list = self.generate_sources_list(instrument_data_model)
        
        return {
            'parameter_tree': parameter_tree_dict,
            'gui_methods': gui_methods_dict,
            'other_methods': other_methods_dict,
            'sources': sources_list
        }

    def set_current_instrument(self, instrument):
        self.current_instrument = instrument
        logger.debug(f"Current instrument set to: {self.current_instrument}")

    def parse_source_file(self, path: str) -> dict:
        logger.debug(f"Initiating parse of source file: {path}")
        with open(path, 'r') as file:
            source = file.read()
        tree = ast.parse(source, filename=path)
        visitor = InstrumentVisitor()
        visitor.visit(tree)
        logger.debug(f"Completed parsing. Extracted instruments: {list(visitor.instruments.keys())}")
        return visitor.instruments

    def generate_gui_methods_dict(self, instrument_data: dict) -> dict:
        logger.info("📂 Generating the GUI methods dictionary... 📂")
        gui_methods_dict = {}
        for class_name, class_info in instrument_data.items():
            for method_name, method_info in class_info.get('gui_methods', {}).items():
                gui_methods_dict[method_name] = method_info
        logger.info("✅ Finished generating the GUI methods dictionary ✅")
        return gui_methods_dict

    def generate_other_methods_dict(self, instrument_data: dict) -> dict:
        logger.info("📂 Generating the other methods dictionary... 📂")
        other_methods_dict = {}
        for class_name, class_info in instrument_data.items():
            for method_name, method_info in class_info.get('other_methods', {}).items():
                other_methods_dict[method_name] = method_info
        logger.info("✅ Finished generating the other methods dictionary ✅")
        return other_methods_dict

    def generate_sources_list(self, instrument_data: dict) -> list:
        logger.info("🔍 Generating sources list... 🔍")
        for class_name, class_info in instrument_data.items():
            if 'sources' in class_info:
                logger.info(f"✅ Sources found for {class_name}: {class_info['sources']} ✅")
                return class_info['sources']
        logger.warning("⚠️ No sources found in the instrument data ⚠️")
        return []

    def generate_properties_list(self, properties: list, class_name: str, index: int = None, subsystem: str = None) -> list:
        logger.debug(f"🚀 Generating properties list for class '{class_name}' with index '{index}'.")
        properties_list = []
        for prop in properties:
            param_dict = self.construct_param_dict(prop, class_name, index, subsystem=subsystem)
            if param_dict is not None:
                properties_list.append(param_dict)
                logger.debug(f"✅ Added property '{prop.get('name')}' with path '{param_dict.get('property_path')}'.")
        logger.debug(f"🏁 Finished generating properties list for '{class_name}': Total properties {len(properties_list)}.")
        return properties_list

    def construct_param_dict(self, prop: dict, class_name: str, index: int = None, subsystem: str = None) -> dict:
        logger.debug(f"🚀 Constructing parameter dict for '{prop.get('name')}' in '{class_name}'")
        # Build a UI-friendly property path.
        property_path = f"{class_name.lower()}"
        if subsystem and subsystem.lower() != class_name.lower():
            property_path += f".{subsystem.lower()}"
        if index is not None:
            property_path += f"[{index}]"
            logger.debug(f"📊 Index provided. Appended to property path: [{index}] 📊")
        property_path += f".{prop.get('name')}"
        logger.debug(f"✅ Property path constructed: {property_path}")

        original_type = prop.get('type', '')
        ui_type = original_type.lower()
        if ui_type == "valueproperty":
            ui_type = "float"
        elif ui_type == "selectproperty":
            ui_type = "list"
        elif ui_type == "switchproperty":
            ui_type = "bool"
        elif ui_type == "stringproperty":
            ui_type = "str"
        param_dict = {
            'name': prop.get('name'),
            'type': ui_type,
            'property_path': property_path,
            'value': None,
            'default': None,
            'readonly': prop.get('access', 'read-write') == 'read',
        }

        if original_type.lower() == 'selectproperty':
            choices = prop.get('choices')
            param_dict.update({
                'type': 'list',
                'limits': choices,
                'value': choices[0] if choices and len(choices) > 0 else None
            })
        elif original_type.lower() == 'valueproperty':
            param_dict.update({
                'type': ui_type,
                'limits': prop.get('range'),
                'value': 0.0
            })
        elif original_type.lower() == 'switchproperty':
            param_dict.update({
                'type': 'bool',
                'value': False
            })
        elif original_type.lower() == 'stringproperty':
            param_dict.update({
                'type': 'str',
                'value': ''
            })
        elif original_type.lower() == 'dataproperty':
            # Skip DataProperty for now.
            return None

        if 'units' in prop:
            param_dict['suffix'] = prop['units']
            param_dict['siPrefix'] = bool(prop['units'])
            logger.debug(f"📏 Setting units for '{prop.get('name')}' to '{prop.get('units')}' 📏")
        else:
            logger.debug(f"🚫 No units found for '{prop.get('name')}' during construction 🚫")

        logger.debug(f"✨ Constructed parameter dict for '{prop.get('name')}': {param_dict} ✨")
        return param_dict

    def generate_parameter_tree_dict(self, instrument_data: dict) -> list:
        """
        Generates a parameter tree structure (as a list of dictionaries) from the instrument data.
        This structure is meant to be passed to pyqtgraph's Parameter.create().
        """
        logger.debug("🌳 Starting to generate the parameter tree... 🌳")
        tree_dict = []
        for class_name, class_info in instrument_data.items():
            logger.debug(f"🔍 Processing class: {class_name}")
            # Create a group for the instrument.
            class_group = {
                'name': class_name,
                'type': 'group',
                'children': []
            }
            # Add a Sources group.
            sources_group = {
                'name': 'Sources',
                'type': 'group',
                'children': []
            }
            sources_list = class_info.get('sources', [])
            for source in sources_list:
                source_param = {
                    'name': source,
                    'type': 'bool',
                    'value': False,
                    'default': None
                }
                sources_group['children'].append(source_param)
            class_group['children'].append(sources_group)
            # Add top-level properties (if any).
            props = class_info.get('properties', [])
            if props:
                props_group = {
                    'name': 'Properties',
                    'type': 'group',
                    'children': self.generate_properties_list(props, class_name)
                }
                class_group['children'].append(props_group)
            # Add each subsystem as its own group.
            for subsystem_name, subsystem_info in class_info.get('subsystems', {}).items():
                logger.debug(f"🛠 Creating subsystem group: {subsystem_name}")
                subsystem_group = self.create_subsystem_group(subsystem_name, subsystem_info)
                if subsystem_group:  # Only add if not None
                    class_group['children'].append(subsystem_group)
            tree_dict.append(class_group)
            logger.debug(f"🌲 Added class group: {class_name} to the tree 🌲")
        logger.debug(f"🚀 Generated parameter tree dictionary: {json.dumps(tree_dict, indent=2)} 🚀")
        logger.debug("🏁 Finished generating the parameter tree 🏁")
        return tree_dict

    def create_subsystem_group(self, subsystem_name, subsystem_info: dict) -> dict:
        logger.debug(f"🔧 Starting to create subsystem group for: {subsystem_name}")
        
        # Check if this subsystem has any properties or children
        # If not, return None to skip this subsystem
        has_properties = bool(subsystem_info.get('properties', []))
        has_instances = bool(subsystem_info.get('instances', {}))
        
        if not has_properties and not has_instances:
            logger.debug(f"Skipping empty subsystem: {subsystem_name}")
            return None  # Skip empty subsystems
        
        if subsystem_info.get('needs_indexing', False):
            logger.debug(f"⚙️ {subsystem_name} requires indexing ⚙️")
            parent_group = {
                'name': subsystem_name,
                'type': 'group',
                'children': []
            }
            # If 'instances' is empty, create groups based on the 'indices' value.
            instances = subsystem_info.get('instances', {})
            if not instances:
                indices = subsystem_info.get('indices', 1)
                for i in range(1, indices + 1):
                    indexed_group = {
                        'name': f"{subsystem_name}{i}",
                        'type': 'group',
                        'children': self.generate_properties_list(subsystem_info.get('properties', []), subsystem_name)
                    }
                    parent_group['children'].append(indexed_group)
                    logger.debug(f"📚 Added indexed group for {subsystem_name}{i} 📚")
            else:
                for index, instance_info in instances.items():
                    indexed_group = {
                        'name': f"{subsystem_name}{index}",
                        'type': 'group',
                        'children': self.generate_properties_list(instance_info.get('properties', []), subsystem_name, index=index)
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
                'children': self.generate_properties_list(subsystem_info.get('properties', []), subsystem_name)
            }
            logger.debug(f"✨ Finished creating group for non-indexed subsystem: {subsystem_name} ✨")
            return group

if __name__ == "__main__":
    factory = InstrumentFactory()
    # Construct the path relative to this file.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(current_dir, '../..', 'drivers', 'instruments', 'hs9000.py')
    path = os.path.abspath(path)
    instrument_data = factory.create_instrument_data_from_driver(path)
    print(json.dumps(instrument_data, indent=2))
    print(instrument_data)
