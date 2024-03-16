import ast
from pathlib import Path
from pyqtgraph.parametertree import Parameter
import logging

logger = logging.getLogger(__name__)

# TODO This is Subsystem Control Factory. Rename and adjust instrument_gui.
class GuiFactory:
    def __init__(self):
        pass  # No initialization required for now

    def create_parameters_from_driver(self, path, instance):
        """
        Create a parameter tree from a Python source file that defines instrument and subsystem classes.

        Args:
            path (str): The path to the Python source file.
            instance (object): The instance of the class where the actions will be called.

        Returns:
            Parameter: A pyqtgraph Parameter object representing the instrument and its properties and actions.
        """
        logger.debug(f"Creating parameters from driver: {path}")
        classes = self.parse_source_file(path)
        parameter_tree_dict = self.generate_parameter_tree_dict(classes, instance)
        return Parameter.create(name='params', type='group', children=parameter_tree_dict)

    @staticmethod
    def parse_source_file(path):
        """
        Parse a Python source file to extract instrument and subsystem class information.

        Args:
            path (str): The path to the Python source file.

        Returns:
            dict: A dictionary representing the classes, their properties, and methods found in the file.
        """
        logger.debug(f"Parsing source file: {path}")
        with open(path, 'r') as file:
            source = file.read()
        tree = ast.parse(source, filename=path)
        visitor = PyMetrClassVisitor()
        visitor.visit(tree)
        return visitor.classes

    def create_data_fetch_action_callback(self, property_name, instance):
        """
        Creates a callback for fetching data for data properties.
        """
        def action_callback():
            logger.info(f"Fetching data for {property_name}")
            data_value = getattr(instance, property_name)()
            logger.info(f"Data fetched for {property_name}: {data_value}")
        return action_callback

    def create_method_action_callback(self, method_name, instance):
        """
        Creates a callback for executing methods.
        """
        def action_callback():
            logger.info(f"Executing method {method_name}")
            method = getattr(instance, method_name, None)
            if callable(method):
                method()
                logger.info(f"Executed method {method_name}")
            else:
                logger.error(f"Method {method_name} not callable or does not exist")
        return action_callback
    
    def _construct_method_dict(self, method_name, instance):
        """
        Construct a dictionary for a method that includes an action button in the GUI.

        Args:
            method_name (str): Name of the method.
            instance (object): Instance of the class where the method exists.

        Returns:
            dict: A dictionary representing the action parameter configuration.
        """
        # Define the action callback
        def action_callback():
            method = getattr(instance, method_name, None)
            if callable(method):
                method()
                logger.info(f"Executed method {method_name}")
            else:
                logger.error(f"Method {method_name} is not callable or does not exist on {instance}")

        # Construct the method dictionary
        method_dict = {
            'name': method_name,
            'type': 'action',
            'value': 'Execute',  # This will be the button text in the GUI
            'action': action_callback
        }
        return method_dict
    
    def _construct_param_dict(self, prop, class_name, instance):
        """
        Construct a parameter dictionary for a given property. This method should handle different types of properties
        including data properties and regular properties.

        Args:
            prop (dict): Property information including name and type.
            class_name (str): Name of the class the property belongs to.
            instance (object): Instance of the class where the property exists.

        Returns:
            dict: A dictionary representing the parameter configuration.
        """
        logger.debug(f"Constructing parameter dictionary for {class_name}.{prop['name']}")
        param_dict = {
            'name': prop['name'],  # 'name' is expected to always be present
            'type': prop['type'],  # 'type' is also expected to always be present
            'doc': prop.get('doc_str', ''),  # Optional, provide default if missing
            'property_path': f"{class_name}.{prop['name']}",  # Constructed from always-present 'name'
        }

        # Handling for 'select_property'
        if prop['type'] == 'select_property':
            choices = prop.get('choices', [])
            param_dict.update({
                'type': 'list',
                'limits': choices,
                'value': choices[0] if choices else None,
            })

        # Handling for 'value_property'
        elif prop['type'] == 'value_property':
            limits = prop.get('range', (None, None))
            limits = [None if v is None else v for v in limits]  # Correctly handle 'None' values
            param_dict.update({
                'type': prop.get('value_type', 'float'),  # Default to 'float' if 'value_type' not specified
                'limits': limits,
                'value': 0,  # Default value
            })

        # Handling for 'switch_property'
        elif prop['type'] == 'switch_property':
            param_dict.update({
                'type': 'bool',
                'value': False,  # Default value
            })

        # Handling for 'data_property'
        if prop['type'] == 'data_property':
            param_dict.update({
                'type': 'action',
                'value': 'Fetch Data',  # Button label
                'action': self.create_data_fetch_action_callback(prop['name'], instance),
            })

        # Handling if the property is marked as a method
        if prop.get('is_method', False):
            param_dict.update({
                'type': 'action',
                'value': 'Execute',  # Button label for method execution
                'action': self.create_method_action_callback(prop['name'], instance),
            })

        logger.debug(f"Constructed param dict for {class_name}.{prop['name']} with type {prop['type']}, action: {'Execute' if 'action' in param_dict else 'None'}")
        return param_dict
    
    def generate_parameter_tree_dict(self, classes, instance):
        """
        Given a dictionary of classes with their properties and methods, generate a dictionary
        suitable for creating a pyqtgraph Parameter tree.

        Args:
            classes (dict): A dictionary of class names to their properties and methods.
            instance (object): The instance of the class where the actions will be called.

        Returns:
            list: A list of dictionaries representing the parameter tree structure.
        """
        logger.debug("Starting to generate parameter tree dictionary...")
        tree_dict = []
        for class_name, class_info in classes.items():
            logger.debug(f"Processing class: {class_name}")
            class_dict = {'name': class_name, 'type': 'group', 'children': []}
            for prop in class_info.get('properties', []):
                logger.debug(f"Constructing parameter dictionary for property: {prop['name']}")
                param_dict = self._construct_param_dict(prop, class_name, instance)  # Ensure this method accepts instance
                if param_dict:
                    logger.debug(f"Adding parameter dict to class_dict: {param_dict}")
                    class_dict['children'].append(param_dict)

            for method_name in class_info.get('methods', []):
                logger.debug(f"Constructing method dictionary for method: {method_name}")
                method_dict = self._construct_method_dict(method_name, instance)  # Using a dedicated method for clarity
                logger.debug(f"Adding method dict to class_dict: {method_dict}")
                class_dict['children'].append(method_dict)

            logger.debug(f"Adding class_dict to tree_dict: {class_dict}")
            tree_dict.append(class_dict)
        logger.debug("Parameter tree dictionary generation completed.")
        return tree_dict

class PyMetrClassVisitor(ast.NodeVisitor):
    """
    AST Node Visitor to parse Python classes for Subsystems and Instruments.
    Collects properties and methods defined in the classes.
    """
    def __init__(self):
        self.classes = {}
        logger.debug("Initialized PyMetrClassVisitor")

    def visit_ClassDef(self, node):
        """
        Visits Class Definitions in the AST and identifies if they represent a Subsystem or Instrument.
        Extracts properties and methods from these classes.
        """
        # Check if the class is a Subsystem or Instrument
        is_target_class = any(base.id in ['Subsystem', 'Instrument'] for base in node.bases if isinstance(base, ast.Name))
        if not is_target_class:
            return

        properties = []
        methods = []
        # Extract properties and methods
        for item in node.body:
            if isinstance(item, ast.Assign):
                prop_details = self.handle_assignment(item)
                if prop_details:
                    properties.append(prop_details)
            elif isinstance(item, ast.FunctionDef) and not item.name.startswith('__'):
                methods.append(item.name)
        
        if properties or methods:
            self.classes[node.name] = {'properties': properties, 'methods': methods}
            logger.info(f"Found class {node.name} with {len(properties)} properties and {len(methods)} methods")

    def handle_assignment(self, node):
        """
        Handles assignment nodes within the class to identify property definitions.
        """
        # Identify property assignment if it's a call to a known property factory function
        if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id'):
            prop_func_id = node.value.func.id
            if prop_func_id in ['switch_property', 'select_property', 'value_property', 'data_property']:
                prop_name = node.targets[0].id
                prop_details = self.parse_property_details(node.value, prop_func_id)
                if prop_details:
                    prop_details['name'] = prop_name
                    logger.debug(f"Identified property {prop_name} of type {prop_func_id}")
                    return prop_details
        return None

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
        if isinstance(node, ast.Str):  # Legacy support
            return node.s
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        logger.error(f"Unhandled node type: {type(node).__name__}")
        return "Unknown"

    
