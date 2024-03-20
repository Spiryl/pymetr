import logging
logger = logging.getLogger(__name__)

import ast
from pyqtgraph.parametertree import Parameter

class InstrumentFactory:
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
        logger.debug(f"🚀 Creating parameters from driver: {path}")
        classes = self.parse_source_file(path)
        logger.debug(f"Generating parameter disctionary from class tree: {instance}")
        parameter_tree_dict = self.generate_parameter_tree_dict(classes, instance)
        logger.debug(f"Generated and returning parameter disctionary: {parameter_tree_dict}")
        return Parameter.create(name='params', type='group', children=parameter_tree_dict)

    @staticmethod
    def parse_source_file(path):
        """
        Parse a Python source file to extract instrument and subsystem class information.
        Now with more verbose logging to provide detailed insights into the parsing process.
        """
        logger.debug(f"🚀 Initiating parse of source file: {path}") 
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

    def construct_param_dict(self, prop, class_name, instance, index=None):
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
        logger.debug(f"🚀 Starting parameter dictionary construction for property '{prop['name']}' of class '{class_name}'.")

        # Initializing the param_dict with the property_path taking index into account if provided
        param_dict = {
            'name': prop['name'],
            'type': prop['type'],
            'doc': prop.get('doc_str', ''),
            'property_path': f"{class_name.lower()}{f'[{index}]' if index is not None else ''}.{prop['name']}",
        }
        logger.debug(f"📘 Basic param_dict setup: {param_dict}")

        if prop['type'] == 'select_property':
            choices = prop.get('choices', [])
            param_dict.update({
                'type': 'list',
                'limits': choices,
                'value': choices[0] if choices else None,
            })
            logger.debug(f"📋 'select_property' handled with choices: {choices}")

        elif prop['type'] == 'value_property':
            limits = prop.get('range', (None, None))
            limits = [None if v is None else v for v in limits]
            param_dict.update({
                'type': prop.get('value_type', 'float'),  # Ensuring 'float' is explicitly set for 'value_property'
                'limits': limits,
                'value': 0,
            })
            logger.debug(f"📐 'value_property' handled with limits: {limits}")

        elif prop['type'] == 'switch_property':
            param_dict.update({
                'type': 'bool',
                'value': False,
            })
            logger.debug(f"🔘 'switch_property' handled with default value: False")

        elif prop['type'] == 'data_property':
            param_dict.update({
                'type': 'action',
                'value': 'Fetch Data',
                'action': self.create_data_fetch_action_callback(prop['name'], instance),
            })
            logger.debug(f"💾 'data_property' handled with action to fetch data.")

        elif prop.get('is_method', False):
            param_dict.update({
                'type': 'action',
                'value': 'Execute',
                'action': self.create_method_action_callback(prop['name'], instance),
            })
            logger.debug(f"🏃 Property marked as method handled with execution action.")

        else:
            # For unrecognized types, don't drop support; instead, handle them appropriately
            # If the type is specifically 'float' or 'int', you could add specific handling here
            logger.debug(f"🚫 Property '{prop['name']}' of class '{class_name}' has an unrecognized type '{prop['type']}'.")

        logger.debug(f"✅ Finished constructing parameter dict for {class_name}.{prop['name']}: {param_dict}")
        return param_dict

        # if prop['type'] == 'data_property':
        #     param_dict.update({
        #         'type': 'action',
        #         'value': 'Fetch Data',
        #         'action': self.create_data_fetch_action_callback(prop['name'], instance),
        #     })
        #     logger.debug(f"'data_property' handled with action to fetch data.")

        # if prop.get('is_method', False):
        #     param_dict.update({
        #         'type': 'action',
        #         'value': 'Execute',
        #         'action': self.create_method_action_callback(prop['name'], instance),
        #     })
        #     logger.debug(f"Property marked as method handled with execution action.")

        logger.debug(f"Finished constructing parameter dict for {class_name}.{prop['name']}: {param_dict}")
        return param_dict
    
    def create_fetch_trace_action_callback(self, class_name, instance):
        def action_callback():
            logger.debug(f"Fetching data using {class_name}.fetch_trace")
            trace_data = instance.fetch_trace()
            # how do I emit the trace.
            # self.instruments[unique_id]['plot_data_emitter'].plot_data_ready.emit(trace_data)
            logger.debug(f"Trace data: {trace_data}")
        return action_callback
    
    def generate_parameter_tree_dict(self, classes, instance):
        tree_dict = []

        for class_name, class_info in classes.items():
            # Starting off with creating a group for the class itself
            class_group = {
                'name': class_name,
                'type': 'group',
                'children': []
            }

            # Check if we're dealing with an indexed subsystem
            if 'indices' in class_info:
                # Loop through each index for indexed subsystems
                for index in range(1, class_info['indices'] + 1):
                    indexed_group = {
                        'name': f"{class_name} {index}",
                        'type': 'group',
                        'children': []
                    }

                    # Add parameters to each indexed group based on class properties
                    for prop in class_info.get('properties', []):
                        # Adjust the construct_param_dict call as necessary to include indexing
                        # Note: You might need to modify construct_param_dict to accept and handle an index parameter
                        param_dict = self.construct_param_dict(prop, class_name, instance, index=index)
                        if param_dict:  # Ensure param_dict is not None or empty
                            indexed_group['children'].append(param_dict)
                    
                    class_group['children'].append(indexed_group)
            else:
                # Non-indexed class, directly add properties to the class group
                for prop in class_info.get('properties', []):
                    param_dict = self.construct_param_dict(prop, class_name, instance)
                    if param_dict:  # Ensure param_dict is not None or empty
                        class_group['children'].append(param_dict)

            tree_dict.append(class_group)
        
        return tree_dict

class PyMetrClassVisitor(ast.NodeVisitor):
    """
    AST Node Visitor to parse Python classes for Subsystems and Instruments.
    Collects properties and methods defined in the classes.
    """
    def __init__(self):
        super().__init__()
        self.classes = {}
        self.indexed_subsystems_info = {}
        self.current_class_name = None

    def visit_ClassDef(self, node):
        logger.debug(f"🚀 Visiting ClassDef: {node.name}")
        self.this = node.name
        class_info = {
            'properties': [],
            'methods': [],
            'indices': None,  # Initialize 'indices' here; will be set if detected
        }
        self.classes[self.this] = class_info
        has_fetch_trace = False

        for item in node.body:
            if isinstance(item, ast.Assign):
                prop_details = self.handle_assignment(item)
                if prop_details:
                    self.classes[self.this]['properties'].append(prop_details)
            elif isinstance(item, ast.FunctionDef):
                self.classes[self.this]['methods'].append(item.name)
                if item.name == 'fetch_trace':
                    has_fetch_trace = True

        is_subsystem_or_instrument = any(base.id in ['Instrument', 'Subsystem'] for base in node.bases if isinstance(base, ast.Name))

        if is_subsystem_or_instrument:
            self.classes[node.name] = {
                'properties': properties,
                'methods': methods,
                'has_fetch_trace': has_fetch_trace
            }
            logger.debug(f"Registered class: {node.name} with properties and methods.")

        init_method = next((n for n in node.body if isinstance(n, ast.FunctionDef) and n.name == '__init__'), None)
        if init_method:
            logger.debug(f"Found __init__ method in {node.name}.")
            self.handle_init_method(init_method)

    def visit_Assign(self, node):
        # This assumes 'self.channel = Channel.build(self, ':CHANnel', indices=4)' pattern
        if isinstance(node.value, ast.Call) and getattr(node.value.func, 'attr', '') == 'build':
            class_name = node.value.func.value.id
            indices = next((kw.value.n for kw in node.value.keywords if kw.arg == 'indices'), None)
            if class_name in self.classes and indices:
                self.classes[class_name]['indices'] = indices

    def handle_init_method(self, method_node):
        logger.debug(f"🚀 Handling __init__ method in class {self.current_class_name}.")
        for expr in method_node.body:
            if isinstance(expr, ast.Assign):
                self.handle_assignment(expr)

    def visit_FunctionDef(self, node):
        # Assuming you already capture methods, just add a check for 'fetch_trace'
        if node.name == 'fetch_trace':
            self.current_class_info['has_fetch_trace'] = True

    def handle_assignment(self, assign_node):
        # Simplify the debug messages and focus on key events

        if isinstance(assign_node.value, ast.Call):
            func = assign_node.value.func
            if hasattr(func, 'attr') and func.attr == 'build' or hasattr(func, 'id') and func.id == 'build':
                logger.debug("🎉 Found 'build' call within assignment.")
                indices = self.extract_build_call_details(assign_node.value)
                # Assuming you have a way to track which class or subsystem this belongs to
                if indices is not None:
                    logger.debug(f"🔢 Handling indices for subsystem: {indices}")
            else:
                logger.debug("Call found in assignment, but not a 'build' call.")
        else:
            logger.debug("Assignment does not contain a call.")

        # Checking for property calls like switch_property, select_property, and value_property
        if isinstance(assign_node.value, ast.Call) and hasattr(assign_node.value.func, 'id'):
            prop_func_id = assign_node.value.func.id
            if prop_func_id in ['switch_property', 'select_property', 'value_property']:
                prop_name = assign_node.targets[0].id
                prop_details = self.parse_property_details(assign_node.value, prop_func_id)
                if prop_details:
                    prop_details['name'] = prop_name
                    logger.debug(f"✅ Found property call '{prop_func_id}' with details: {prop_details}")
                    return prop_details
                else:
                    logger.debug("❗ No property details parsed.")

    def extract_build_call_details(self, call_node):
        keywords = {kw.arg: self.get_ast_node_value(kw.value) for kw in call_node.keywords}
        indices = keywords.get('indices', None)
        if indices:
            logger.debug(f"🎯 Extracted 'indices' from 'build' call: {indices}")
            return indices  # Returning indices directly for further use
        else:
            logger.debug("🚫 'build' call without 'indices'.")
            return None  # Explicitly returning None when no indices found

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
            for kw in call_node.keywords:
                if kw.arg == 'indices':
                    details['indices'] = self.get_ast_node_value(kw.value)
                # Handle other specific keywords similarly...

            if not details.get('indices') and len(call_node.args) > 2:
                # This block checks if 'indices' wasn't found in keywords but you're expecting it
                # in a specific position in args for some property definitions.
                # Adjust the index as per your method signature.
                possible_indices_arg = call_node.args[2]  # Example: Assuming the third argument could be indices
                if isinstance(possible_indices_arg, ast.Constant):  # or ast.Num in older Python versions
                    details['indices'] = possible_indices_arg.value
            else:
                logger.warning(f"Unsupported property function: {prop_func_id}")
        return details

    def get_ast_node_value(self, node):
        """
        Extracts a value from an AST node.
        """
        if isinstance(node, ast.Str):  # Legacy support for Python < 3.8
            # logger.debug(f"Processing a Str node: {node.s}")
            return node.s
        elif isinstance(node, ast.Constant):
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
        elif isinstance(node, ast.Call):
            logger.debug(f"Processing a Call node: {ast.dump(node)}")
            # Here you might want to specifically handle known function calls
            # For example, if extracting 'indices' from a build call, handle accordingly
            if hasattr(node.func, 'attr') and node.func.attr == 'build':
                # This assumes 'build' calls have a specific structure you want to extract from
                # Extract arguments or keywords as needed
                args = [self.get_ast_node_value(arg) for arg in node.args]
                keywords = {kw.arg: self.get_ast_node_value(kw.value) for kw in node.keywords}
                return {"args": args, "keywords": keywords}  # Example structure
            else:
                logger.warning(f"Encountered a Call node that's not handled specifically: {ast.dump(node)}")
                return None
        else:
            logger.error(f"Unhandled node type: {type(node).__name__}")
            return None
        
if __name__ == "__main__":

    def generate_debug_output(parsed_classes):
        logger.debug(f"Completed parsing. Extracted classes: {list(parsed_classes.keys())}")
        for class_name, details in parsed_classes.items():
            properties_str = "\n".join([f"- {prop}" for prop in details.get('properties', [])])
            methods_str = "\n".join([f"- {method}" for method in details.get('methods', [])])
            indices_str = f"index count = {details['indices']}" if details.get('indices') else ""
            logger.debug(f"Class {class_name}: {indices_str}\nProperties:\n{properties_str}\nMethods:\n{methods_str}")

    path = 'pymetr/instruments/DSOX1204G.py'
    with open(path, 'r') as file:
        source = file.read()

    tree = ast.parse(source, filename=path)
    visitor = PyMetrClassVisitor()
    visitor.visit(tree)

    generate_debug_output(visitor.classes)