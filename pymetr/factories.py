import logging
logger = logging.getLogger(__name__)

import ast
from pymetr.visitors import InstrumentVisitor

class InstrumentFactory:
    def __init__(self):
        self.current_instrument = None

    def create_parameters_from_driver(self, path):
        logger.debug(f"Creating parameters from driver: {path}")
        instrument_data = self.parse_source_file(path)  # Parse the source file using the new visitor
        parameter_tree_dict = self.generate_parameter_tree_dict(instrument_data)  
        return parameter_tree_dict
    
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
    
    def generate_properties_list(self, properties, class_name, index=None):
        """
        Generates a list of property dictionaries for a given set of properties, class name, and optional index.
        Each property dictionary is constructed using the construct_param_dict method, ensuring the inclusion
        of the property path. Logging is added for debug purposes to track the property processing flow.

        Args:
            properties (list of dict): List of property information including name and type.
            class_name (str): The name of the class these properties belong to.
            index (optional, int): The index for indexed properties, if applicable.

        Returns:
            list of dict: A list of property dictionaries with added property paths.
        """
        logger.debug(f"🚀 Starting to generate properties list for class '{class_name}' with index '{index}'.")
        properties_list = []
        for prop in properties:
            logger.debug(f"🔍 Processing property '{prop['name']}' of type '{prop['type']}' for class '{class_name}'.")
            # Use construct_param_dict to create the property dictionary
            param_dict = self.construct_param_dict(prop, class_name, index)
            properties_list.append(param_dict)
            logger.debug(f"✅ Added property '{prop['name']}' to properties list with path '{param_dict.get('property_path')}'.")
        
        logger.debug(f"🏁 Finished generating properties list for '{class_name}': Total properties {len(properties_list)}.")
        return properties_list

    def construct_param_dict(self, prop, class_name, index=None):
        """
        Construct a parameter dictionary for a given property. This method should handle different types of properties
        including data properties and regular properties.

        Args:
            prop (dict): Property information including name and type.
            class_name (str): Name of the class the property belongs to.
            instance (object): Instance of the class where the property exists.
            index (int): The index for indexed properties, if applicable.

        Returns:
            dict: A dictionary representing the parameter configuration.
        """
        logger.debug(f"🚀 Starting construct_param_dict for '{prop['name']}' in '{class_name}' 🚀")
        
        # Construct the property path considering indexing
        logger.debug(f"🔍 Checking if '{prop['name']}' needs indexing... 🔍")
        property_path = f"{class_name.lower()}"
        if index is not None:
            logger.debug(f"📊 Index provided. Appending to property path: [{index}] 📊")
            property_path += f"[{index}]"
        property_path += f".{prop['name']}"
        logger.debug(f"✅ Property path constructed: {property_path} ✅")

        # Initialize the param_dict
        logger.debug(f"📝 Initializing parameter dictionary for '{prop['name']}'... 📝")
        param_dict = {
            'name': prop['name'],
            'type': prop['type'],
            'property_path': property_path,
            'value': None  # Default values can be set more intelligently based on the type or other metadata
        }

        logger.debug(f"🔧 Mapping property type '{prop['type']}' to parameter configuration... 🔧")
        if prop['type'] == 'select_property':
            param_dict.update({
                'type': 'list',
                'limits': prop['choices'],
                'value': prop['choices'][0]  # Default to the first choice
            })
            logger.debug(f"📋 Updated for select_property: {param_dict} 📋")
        elif prop['type'] == 'value_property':
            limits = prop.get('range', (None, None))
            param_dict.update({
                'type': 'float',  # Assuming all value_properties are of float type
                'limits': limits,
                'value': 0.0  # Default to 0.0 for floats
            })
            logger.debug(f"📐 Updated for value_property: {param_dict} 📐")
        elif prop['type'] == 'switch_property':
            param_dict.update({
                'type': 'bool',
                'value': False  # Default to False
            })
            logger.debug(f"🔲 Updated for switch_property: {param_dict} 🔲")
        elif prop['type'] in ['float', 'int']:
            param_dict.update({
                'limits': prop.get('range', [None, None]),
                'value': 0  # Default to 0 for both int and float
            })
            logger.debug(f"🔢 Updated for numeric type: {param_dict} 🔢")

        # Uncomment or modify this section according to your requirements for actions or data properties
        # logger.debug(f"🖇 Checking for action or data properties... 🖇")
        # if prop.get('is_action', False) or prop.get('is_data', False):
        #     # Logic for handling actions or data properties
        #     logger.debug(f"⚙️ Handling action/data property: {prop['name']} ⚙️")

        logger.debug(f"✨ Constructed parameter dict for '{prop['name']}': {param_dict} ✨")
        return param_dict

    def create_action_callback(self, method_name, instance, is_data=False):
        """
        Create a callback function for a method or data property.

        Args:
            method_name (str): The name of the method or data property.
            instance (object): The instance of the class where the method is called.
            is_data (bool): Flag to determine if it's a data property fetching data.

        Returns:
            function: A callback function to be connected to the action.
        """
        def action_callback():
            if is_data:
                logger.debug(f"Fetching data using {method_name}")
                return getattr(instance, method_name)()  # Call the method to fetch data
            else:
                logger.debug(f"Executing method {method_name}")
                getattr(instance, method_name)()  # Call the method without expecting a return

        return action_callback
    
    def create_fetch_trace_action_callback(self, fetch_trace_method):
        def action_callback():
            trace_data = fetch_trace_method()
            logger.debug(f"Trace data: {trace_data}")
        return action_callback
    
    def generate_parameter_tree_dict(self, instrument_data):
        """
        Generates a parameter tree dictionary from the instrument data, including action parameters
        and subsystems with their properties. Emojis and logging added for clarity and debugging.

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

            if 'action_parameters' in class_info:
                logger.debug(f"🎬 Adding action parameters for {class_name} 🎬")
                for action_param, is_enabled in class_info['action_parameters'].items():
                    if is_enabled and action_param == 'fetch_trace':
                        logger.debug(f"📈 Adding fetch_trace action for {class_name} 📈")
                        class_group['children'].append({
                            'name': action_param,
                            'type': 'action',
                            'action': self.create_fetch_trace_action_callback(self.current_instrument.fetch_trace)
                        })

            for subsystem_name, subsystem_info in class_info.get('subsystems', {}).items():
                logger.debug(f"🛠 Creating subsystem group: {subsystem_name} 🛠")
                subsystem_group = self.create_subsystem_group(subsystem_name, subsystem_info)
                class_group['children'].append(subsystem_group)

            tree_dict.append(class_group)
            logger.debug(f"🌲 Added class group: {class_name} to the tree 🌲")

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
           # Load a test driver
            path = 'pymetr/instruments/DSOX1204G.py'  
            with open(path, 'r') as file:
                source = file.read()



            tree = ast.parse(source, filename=path)

            # Assuming PyMetrClassVisitor is your revised visitor class
            visitor = InstrumentVisitor()
            visitor.visit(tree)  # First pass to identify structure

            print_consolidated_view(visitor.instruments)
            print(visitor.instruments)