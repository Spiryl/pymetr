import logging
logger = logging.getLogger(__name__)

import ast
from pyqtgraph.parametertree import Parameter

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
        Now with more verbose logging to provide detailed insights into the parsing process.
        """
        logger.debug(f"Initiating parse of source file: {path}") 
        with open(path, 'r') as file:
            source = file.read()
        tree = ast.parse(source, filename=path)
        visitor = PyMetrClassVisitor()
        visitor.visit(tree)
        logger.debug(f"Completed parsing. Extracted classes: {list(visitor.classes.keys())}")  # Spill the tea on what we found
        for class_name, details in visitor.classes.items():
            properties_str = "\n".join([f"- {prop}" for prop in details.get('properties', [])])
            methods_str = "\n".join([f"- {method}" for method in details.get('methods', [])])
            logger.debug(f"Class {class_name}:\nProperties:\n{properties_str}\nMethods:\n{methods_str}")
        return visitor.classes

    # def create_data_fetch_action_callback(self, property_name, instance):
    #     """
    #     Creates a callback for fetching data for data properties.
    #     """
    #     def action_callback():
    #         logger.debug(f"Fetching data for {property_name}")
    #         data_value = getattr(instance, property_name)()
    #         logger.debug(f"Data fetched for {property_name}: {data_value}")
    #     return action_callback

    # def create_fetch_trace_action_callback(self, instance):
    #     """
    #     Creates a callback for the fetch_trace action. This method is triggered when the fetch_trace action is activated in the GUI.
        
    #     Args:
    #         instance (object): The instance of the instrument class.
    #     """
    #     def action_callback():
    #         logger.debug("Fetching trace data...")
    #         trace_data = instance.fetch_trace()
    #         # Handle the fetched trace data as needed, e.g., plot it or log it
    #         # This is where you would integrate with your plotting or data handling mechanism
    #         logger.debug(f"Fetched trace data: {trace_data}")
        
    #     return action_callback

    # def create_method_action_callback(self, method_name, instance):
    #     """
    #     Creates a callback for executing methods.
    #     """
    #     def action_callback():
    #         logger.debug(f"Executing method {method_name}")
    #         method = getattr(instance, method_name, None)
    #         if callable(method):
    #             method()
    #             logger.debug(f"Executed method {method_name}")
    #         else:
    #             logger.error(f"Method {method_name} not callable or does not exist")
    #     return action_callback
 
    # def construct_fetch_trace_action(self, instance):
    #     """
    #     Construct the action parameter dictionary for the fetch_trace method.

    #     Args:
    #         instance (object): The instance of the instrument class that contains the fetch_trace method.
            
    #     Returns:
    #         dict: The parameter dictionary for the fetch_trace action.
    #     """
    #     return {
    #         'name': 'fetch_trace',
    #         'type': 'action',
    #         'title': 'Fetch Trace',
    #         'visible': True,
    #         'action': lambda: self.create_fetch_trace_action_callback(instance)
    #     }
    
    # def _construct_method_dict(self, method_name, instance):
    #     """
    #     Construct a dictionary for a method that includes an action button in the GUI.

    #     Args:
    #         method_name (str): Name of the method.
    #         instance (object): Instance of the class where the method exists.

    #     Returns:
    #         dict: A dictionary representing the action parameter configuration.
    #     """
    #     # Define the action callback
    #     def action_callback():
    #         method = getattr(instance, method_name, None)
    #         if callable(method):
    #             method()
    #             logger.debug(f"Executed method {method_name}")
    #         else:
    #             logger.error(f"Method {method_name} is not callable or does not exist on {instance}")

    #     # Construct the method dictionary
    #     method_dict = {
    #         'name': method_name,
    #         'type': 'action',
    #         'title': 'Execute',  # For better clarity in the GUI
    #         'action': action_callback
    #     }
    #     return method_dict
    
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
            'property_path': f"{class_name.lower()}.{prop['name']}",  # Constructed from always-present 'name'
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
        Modify the dictionary generation to handle indexed subsystems by creating a group for each
        indexed instance and populating it with parameters.

        Args:
            classes (dict): A dictionary of class names to their properties and methods.
            instance (object): The instance of the class where the actions will be called.

        Returns:
            list: A list of dictionaries representing the parameter tree structure, now including indexed subsystems.
        """
        logger.debug("Generating parameter tree dictionary, now with indexed subsystem handling...")
        tree_dict = []

        for class_name, class_info in classes.items():
            logger.debug(f"Processing class: {class_name}")
            class_dict = {'name': class_name, 'type': 'group', 'children': []}

            # Check if 'fetch_trace' method is present and add an action parameter for it
            if class_info.get('has_fetch_trace', False):
                fetch_trace_param = {
                    'name': 'Fetch Trace',
                    'type': 'action',
                    'action': lambda: self.handle_fetch_trace(instance)
                }
                class_dict['children'].append(fetch_trace_param)

            for prop in class_info.get('properties', []):
                # Direct handling of indexed subsystems
                if prop['type'] == 'build' and 'indices' in prop:
                    for index in range(1, prop['indices'] + 1):  # Assuming 1-based indexing
                        indexed_group_name = f"{prop['name']} {index}"
                        # Create a group for each indexed instance, populating with parameters
                        indexed_group = {
                            'name': indexed_group_name,
                            'type': 'group',
                            'children': []
                        }

                        # Here, you'd populate each indexed group with parameters
                        # This could involve calling a modified version of _construct_param_dict
                        # or directly adding parameters based on the class_info
                        for subprop in class_info.get('properties', []):
                            if subprop['type'] != 'build':  # Avoid recursive builds
                                param_dict = self._construct_param_dict(subprop, class_name, instance, prefix=indexed_group_name)
                                indexed_group['children'].append(param_dict)

                        class_dict['children'].append(indexed_group)
                else:
                    # Handling non-indexed properties as usual
                    param_dict = self._construct_param_dict(prop, class_name, instance)
                    if param_dict:
                        class_dict['children'].append(param_dict)

            tree_dict.append(class_dict)
        logger.debug("Completed parameter tree dictionary generation with indexed subsystem handling.")
        
        return tree_dict

class PyMetrClassVisitor(ast.NodeVisitor):
    """
    AST Node Visitor to parse Python classes for Subsystems and Instruments.
    Collects properties and methods defined in the classes.
    """
    def __init__(self):
        super().__init__()
        self.classes = {}

    def visit_ClassDef(self, node):
        # Initialize placeholders for properties and methods
        properties = []
        methods = []
        has_fetch_trace = False

        # Process each item in the class body
        for item in node.body:
            if isinstance(item, ast.Assign):
                # Process assignments (likely properties)
                prop_details = self.handle_assignment(item)
                if prop_details:
                    properties.append(prop_details)
            elif isinstance(item, ast.FunctionDef):
                # Add method name to the list
                methods.append(item.name)
                # Check specifically for 'fetch_trace'
                if item.name == 'fetch_trace':
                    has_fetch_trace = True

        # Check if the class is a subclass of Instrument or Subsystem (simplified check)
        is_instrument = any(base.id == 'Instrument' for base in node.bases if isinstance(base, ast.Name))

        # If it's an instrument, add to our classes dict
        if is_instrument:
            self.classes[node.name] = {
                'properties': properties,
                'methods': methods,
                'has_fetch_trace': has_fetch_trace
            }

    def visit_FunctionDef(self, node):
        # Assuming you already capture methods, just add a check for 'fetch_trace'
        if node.name == 'fetch_trace':
            self.current_class_info['has_fetch_trace'] = True

    def handle_assignment(self, node):
        # This is a placeholder for your existing property parsing logic
        # Return a dictionary with property details
        return {'name': node.targets[0].id}  # Simplified example

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