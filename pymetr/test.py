import ast
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
from copy import deepcopy
import ast

class InstrumentVisitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.instruments = {}
        self.current_instrument = None

    def visit_ClassDef(self, node):
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        if 'Instrument' in bases:
            self.current_instrument = node.name
            self.instruments[node.name] = {
                'subsystems': {}, 
                'properties': [], 
                'methods': [],
                'action_parameters': {}  # Preparing to capture special methods like fetch_trace
            }
            
            # Look for the fetch_trace method directly in the current class definition
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == 'fetch_trace':
                    self.instruments[self.current_instrument]['action_parameters']['fetch_trace'] = True
                    break  # Assuming only one fetch_trace method per class
            
        elif 'Subsystem' in bases and self.current_instrument:
            subsystem_visitor = SubsystemVisitor()
            subsystem_visitor.visit(node)
            subsystem_info = self.instruments[self.current_instrument]['subsystems'][node.name]
            if subsystem_info.get('needs_indexing', False):
                # Duplicate properties and methods for each instance if needed
                for index in range(1, subsystem_info['indices'] + 1):
                    indexed_name = f"{node.name} {index}"
                    subsystem_info['instances'][indexed_name] = deepcopy(subsystem_visitor.properties_methods)
            else:
                # Update properties and methods directly for non-indexed or single-instance subsystems
                self.instruments[self.current_instrument]['subsystems'][node.name].update(subsystem_visitor.properties_methods)
        super().generic_visit(node)  # Continue traversal.

    def visit_Assign(self, node):
        if self.current_instrument and isinstance(node.value, ast.Call) and getattr(node.value.func, 'attr', '') == 'build':
            subsystem_class_name = node.value.func.value.id
            indices = next((self.get_ast_node_value(kw.value) for kw in node.value.keywords if kw.arg == 'indices'), 1)

            # Initialize the subsystem with indexing information and an 'instances' dictionary
            subsystem_info = {
                'indices': indices,
                'needs_indexing': indices > 1,
                'properties': [],
                'methods': [],
                'instances': {} if indices > 1 else None
            }
            self.instruments[self.current_instrument]['subsystems'][subsystem_class_name] = subsystem_info
        super().generic_visit(node)
            
    def get_ast_node_value(self, node):
        """
        Extracts a value from an AST node.
        """
        if isinstance(node, ast.Constant):
            # logger.debug(f"Processing a Constant node: {node.value}")
            return node.value
        elif isinstance(node, ast.Name):
            # logger.debug(f"Processing a Name node: {node.id}")
            return node.id
        elif isinstance(node, ast.List):
            # logger.debug(f"Processing a List node with elements: {node.elts}")
            return [self.get_ast_node_value(el) for el in node.elts]
        elif isinstance(node, ast.UnaryOp):
            # logger.debug(f"Processing a UnaryOp node with operand: {node.operand}")
            operand = self.get_ast_node_value(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
        else:
            logger.error(f"Unhandled node type: {type(node).__name__}")
            return None

class SubsystemVisitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.properties_methods = {'properties': [], 'methods': []}

    def visit_Assign(self, node):
        # Logic to handle assignments within a subsystem class, focusing on properties.
        if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id'):
            prop_func_id = node.value.func.id
            if prop_func_id in ['value_property', 'select_property', 'switch_property']:
                prop_details = self.parse_property_details(node.value, prop_func_id)
                # Ensure 'name' key is properly assigned to prop_details
                if prop_details:
                    prop_name = node.targets[0].id
                    prop_details['name'] = prop_name
                    self.properties_methods['properties'].append(prop_details)
        super().generic_visit(node)

    def visit_FunctionDef(self, node):
        # Method detection could be as simple as adding the method's name to the list,
        # assuming you're only interested in the existence/names of methods, not their signatures or bodies.
        self.properties_methods['methods'].append(node.name)
        super().generic_visit(node)  # Continue traversal.

    def parse_property_details(self, call_node, prop_func_id):
        """
        Parses details from the AST node for property factory function calls.
        """
        details = {'type': prop_func_id}
        if prop_func_id == 'value_property':
            # Parse keywords for additional details like type and range
            for kw in call_node.keywords:
                if kw.arg in ['type', 'range']:
                    details[kw.arg] = self.get_ast_node_value(kw.value)
        elif prop_func_id == 'select_property':
            # Handle selection property specific logic
            if len(call_node.args) > 1:
                choices_arg = call_node.args[1]
                if isinstance(choices_arg, ast.List):
                    details['choices'] = [self.get_ast_node_value(el) for el in choices_arg.elts]
        elif prop_func_id == 'switch_property' or prop_func_id == 'data_property':
            # For now, there's no extra processing needed for these
            pass
        else:
            logger.warning(f"Unsupported property function: {prop_func_id}")

        return details
    
    def get_ast_node_value(self, node):
        """
        Extracts a value from an AST node.
        """
        if isinstance(node, ast.Constant):
            # logger.debug(f"Processing a Constant node: {node.value}")
            return node.value
        elif isinstance(node, ast.Name):
            # logger.debug(f"Processing a Name node: {node.id}")
            return node.id
        elif isinstance(node, ast.List):
            # logger.debug(f"Processing a List node with elements: {node.elts}")
            return [self.get_ast_node_value(el) for el in node.elts]
        elif isinstance(node, ast.UnaryOp):
            # logger.debug(f"Processing a UnaryOp node with operand: {node.operand}")
            operand = self.get_ast_node_value(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
        else:
            logger.error(f"Unhandled node type: {type(node).__name__}")
            return None


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
        Construct a parameter dictionary for a given property, not requiring an instance.
        Args:
            prop (dict): Property information including name and type.
            class_name (str): Name of the class the property belongs to.
            index (int): The index for indexed properties, if applicable.
        Returns:
            dict: A dictionary representing the parameter configuration.
        """
        logger.debug(f"Constructing parameter dictionary for property '{prop['name']}' of class '{class_name}'.")

        # Construct the property path considering indexing
        property_path = f"{class_name.lower()}{f'[{index}]' if index is not None else ''}.{prop['name']}"

        # Use the generate_properties_list logic here to construct the parameter dictionary
        param_dict = {
            'name': prop['name'],
            'type': prop['type'],
            'property_path': property_path,
            'value': None  # This will be set when syncing with the instrument state
        }

        param_dict = self.generate_properties_list([prop])[0]  # Use the new generate_properties_list method
        param_dict['property_path'] = property_path  # Add the property_path to the param_dict

        if prop['type'] == 'action':
            if prop['name'] == 'fetch_trace':
                # Directly use create_fetch_trace_action_callback to tie it with the instance's method
                param_dict['action'] = self.create_fetch_trace_action_callback(instance)
            else:
                # Handle other actions similarly, ensuring they're tied to the correct instance methods
                param_dict['action'] = self.create_action_callback(prop['name'], instance, is_data=prop.get('is_data', False))

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
    
    def create_fetch_trace_action_callback(self, instance):
        """
        Generates a callback function for the 'fetch_trace' action on a given instrument instance.
        Args:
            instance (object): The instrument instance with a 'fetch_trace' method.
        Returns:
            function: A callback function that calls 'fetch_trace' on the given instance.
        """
        def action_callback():
            logger.debug(f"Fetching trace data...")
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
                    'action': self.create_fetch_trace_action_callback(instance)
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
    
if __name__ == "__main__":

    def print_consolidated_view(instrument):
        for instrument_name, instrument_info in instrument.items():
            print(f"{instrument_name}/")

            if instrument_info.get('action_parameters', {}).get('fetch_trace', False):
                print(f"├── fetch_trace()")
            subsystems = instrument_info['subsystems'].items()
            
            for subsystem_name, subsystem_info in subsystems:
                if 'instances' in subsystem_info and subsystem_info['instances']:
                    # For subsystems with indexed instances like Channels
                    print(f"├── {subsystem_name}")
                    for instance_name, instance_info in subsystem_info['instances'].items():
                        print(f"│   ├── {instance_name}")
                        print_properties(instance_info['properties'], is_last=False)
                else:
                    # Directly print subsystem properties when there's no indexing
                    print(f"├── {subsystem_name}")
                    print_properties(subsystem_info['properties'], is_last=False)
            print()  # For a newline after each instrument

    def print_properties(properties, is_last):
        indent = "│   │   " if not is_last else "    "  # Adjust the indentation based on hierarchy
        for prop in properties:
            prop_summary = format_property_summary(prop)
            print(f"{indent}├── {prop_summary}")

    def format_property_summary(prop):
        """Formats a property summary based on its type and details."""
        prop_type = prop.get('type')
        summary_parts = [f"{prop['name']} ({prop_type})"]
        if 'choices' in prop:
            choices_str = ", ".join(prop['choices'])
            summary_parts.append(f"[Choices: {choices_str}]")
        elif 'range' in prop:
            range_str = f"[Range: {prop['range'][0]} to {prop['range'][1]}]"
            summary_parts.append(range_str)
        return " ".join(summary_parts)

    def format_property_summary(prop):
        """Formats a property summary based on its type and details."""
        if prop['type'] == 'select_property':
            return f"{prop['name']} (list) [Choices: {', '.join(prop['choices'])}]"
        elif prop['type'] == 'switch_property':
            return f"{prop['name']} (bool)"
        elif prop['type'] in ['value_property', 'int', 'float']:
            prop_summary = f"{prop['name']} ({prop.get('value_type', prop['type'])})"
            if 'range' in prop:
                prop_summary += f" [Range: {prop['range'][0]} to {prop['range'][1]}]"
            return prop_summary
        return f"{prop['name']} ({prop['type']})"
    
    # Load a test driver
    path = 'pymetr/instruments/DSOX1204G.py'  
    with open(path, 'r') as file:
        source = file.read()

    tree = ast.parse(source, filename=path)

    # Assuming PyMetrClassVisitor is your revised visitor class
    visitor = InstrumentVisitor()
    visitor.visit(tree)  # First pass to identify structure

    print_consolidated_view(visitor.instruments)
    # print(visitor.instruments)

    # Now let's create that InstrumentFactory instance
    factory = InstrumentFactory()

    # And let's pass that visitor.instruments to generate the parameter tree dictionary
    test_tree = factory.generate_parameter_tree_dict(visitor.instruments)

    # Time to see if our tree is growing strong
    from pprint import pprint
    pprint(test_tree)
