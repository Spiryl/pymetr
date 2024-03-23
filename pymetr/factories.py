import logging
logger = logging.getLogger(__name__)

import ast
from pyqtgraph.parametertree import Parameter
from pymetr.visitors import InstrumentVisitor, SubsystemVisitor

class InstrumentFactory:
    def __init__(self):
        pass  # No initialization required for now

    def create_parameters_from_driver(self, path, instance):
        """
        This method remains largely the same but uses the updated visitors and methods.
        """
        logger.debug(f"Creating parameters from driver: {path}")
        instrument_data = self.parse_source_file(path)  # Parse the source file using the new visitor
        parameter_tree_dict = self.generate_parameter_tree_dict(instrument_data, instance)  # Generate the parameter tree
        return Parameter.create(name='params', type='group', children=parameter_tree_dict)

    def parse_source_file(self, path):
        """
        Replace PyMetrClassVisitor with the new InstrumentVisitor and return its instruments.
        """
        logger.debug(f"Initiating parse of source file: {path}")
        with open(path, 'r') as file:
            source = file.read()
        tree = ast.parse(source, filename=path)
        visitor = InstrumentVisitor()
        visitor.visit(tree) 
        logger.debug(f"Completed parsing. Extracted instruments: {list(visitor.instruments.keys())}")
        return visitor.instruments
    
    def generate_properties_list(self, properties):
        # Function to create the properties list
        properties_list = []
        for prop in properties:
            param_dict = {
                'name': prop['name'],
                'type': prop['type'],
                'value': None  # Placeholder, actual value should be set by syncing with the instrument
            }
            
            if prop['type'] == 'select_property':
                param_dict.update({
                    'type': 'list',
                    'values': prop['choices'],
                    'value': prop['choices'][0]  # Default to the first choice
                })
            elif prop['type'] == 'switch_property':
                param_dict.update({
                    'type': 'bool',
                    'value': False  # Default to False
                })
            elif prop['type'] in ['float', 'int']:
                # Assuming 'int' properties can also have a 'range' defined
                range_val = prop.get('range', [None, None])
                param_dict.update({
                    'type': 'float' if prop['type'] == 'float' else 'int',
                    'limits': range_val,
                    'value': 0.0 if prop['type'] == 'float' else 0  # Default to 0 or 0.0
                })
            
            properties_list.append(param_dict)
            
        return properties_list

    def construct_param_dict(self, prop, class_name, instance, index=None):
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
        logger.debug(f"🚀 Constructing parameter dictionary for property '{prop['name']}' of class '{class_name}'.")

        # Construct the property path considering indexing
        property_path = f"{class_name.lower()}"
        if index is not None:
            property_path += f"[{index}]"
        property_path += f".{prop['name']}"

        # Initialize the param_dict
        param_dict = {
            'name': prop['name'],
            'type': prop['type'],
            'property_path': property_path,
            # Default values can be set more intelligently based on the type or other metadata
            'value': None
        }

        # Map the property type to the correct parameter type and any additional properties
        if prop['type'] == 'select_property':
            param_dict.update({
                'type': 'list',
                'values': prop['choices'],
                'value': prop['choices'][0]  # Default to the first choice
            })
        elif prop['type'] == 'value_property':
            limits = prop.get('range', (None, None))
            param_dict.update({
                'type': 'float',  # Assuming all value_properties are of float type
                'limits': limits,
                'value': 0.0  # Default to 0.0 for floats
            })
        elif prop['type'] == 'switch_property':
            param_dict.update({
                'type': 'bool',
                'value': False  # Default to False
            })
        elif prop['type'] in ['float', 'int']:
            param_dict.update({
                'limits': prop.get('range', [None, None]),
                'value': 0  # Default to 0 for both int and float
            })

        # Handle action or data properties if any
        if prop.get('is_action', False) or prop.get('is_data', False):
            # Set up an action type parameter, which will trigger a method when activated
            action = self.create_action_callback(prop['name'], instance, prop.get('is_data', False))
            param_dict.update({
                'type': 'action',
                'value': prop['name'],
                'action': action
            })

        logger.debug(f"Constructed parameter dict: {param_dict}")
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
    
    def create_fetch_trace_action_callback(self, class_name, instance):
        def action_callback():
            logger.debug(f"Fetching data using {class_name}.fetch_trace")
            instance.fetch_trace()
        return action_callback
    
    def generate_parameter_tree_dict(self, instrument_data, instance):
        tree_dict = []

        for class_name, class_info in instrument_data.items():
            # Create a group for the main instrument
            class_group = {
                'name': class_name,
                'type': 'group',
                'children': []
            }

            # Deal with action parameters like fetch_trace first
            if 'action_parameters' in class_info and class_info['action_parameters'].get('fetch_trace', False):
                class_group['children'].append({
                    'name': 'fetch_trace',
                    'type': 'action',
                    'action': self.create_fetch_trace_action_callback(class_name, instance)
                })

            # Loop through subsystems
            for subsystem_name, subsystem_info in class_info['subsystems'].items():
                # Special handling for Channel to put it under a single group
                if subsystem_name == 'Channel':
                    channel_group = {
                        'name': 'Channels',  # Name this group as 'Channels'
                        'type': 'group',
                        'children': []
                    }

                    # For each indexed instance, create a subgroup and populate it
                    for index_name, instance_info in subsystem_info['instances'].items():
                        indexed_group = {
                            'name': index_name,
                            'type': 'group',
                            'children': self.generate_properties_list(instance_info['properties'])
                        }
                        channel_group['children'].append(indexed_group)

                    class_group['children'].append(channel_group)
                else:
                    # Directly create a group for non-indexed subsystems
                    subsystem_group = {
                        'name': subsystem_name,
                        'type': 'group',
                        'children': self.generate_properties_list(subsystem_info['properties'])
                    }
                    class_group['children'].append(subsystem_group)

            tree_dict.append(class_group)

        return tree_dict