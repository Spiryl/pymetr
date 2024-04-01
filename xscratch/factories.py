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
        logger.debug(f"Creating parameters from driver: {path}")
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
        logger.debug(f"Starting parameter dictionary construction for property '{prop['name']}' of class '{class_name}'.")
        
        param_dict = {
            'name': prop['name'],
            'type': prop['type'],
            'doc': prop.get('doc_str', ''),
            'property_path': f"{class_name.lower()}.{prop['name']}",
        }
        logger.debug(f"Basic param_dict setup: {param_dict}")

        if prop['type'] == 'select_property':
            choices = prop.get('choices', [])
            param_dict.update({
                'type': 'list',
                'limits': choices,
                'value': choices[0] if choices else None,
            })
            logger.debug(f"'select_property' handled with choices: {choices}")

        elif prop['type'] == 'value_property':
            limits = prop.get('range', (None, None))
            limits = [None if v is None else v for v in limits]
            param_dict.update({
                'type': prop.get('value_type', 'float'),
                'limits': limits,
                'value': 0,
            })
            logger.debug(f"'value_property' handled with limits: {limits}")

        elif prop['type'] == 'switch_property':
            param_dict.update({
                'type': 'bool',
                'value': False,
            })
            logger.debug(f"'switch_property' handled with default value: False")

        if prop['type'] == 'data_property':
            param_dict.update({
                'type': 'action',
                'value': 'Fetch Data',
                'action': self.create_data_fetch_action_callback(prop['name'], instance),
            })
            logger.debug(f"'data_property' handled with action to fetch data.")

        if prop.get('is_method', False):
            param_dict.update({
                'type': 'action',
                'value': 'Execute',
                'action': self.create_method_action_callback(prop['name'], instance),
            })
            logger.debug(f"Property marked as method handled with execution action.")

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
        """
        Modify the dictionary generation to handle indexed subsystems by creating a group for each
        indexed instance and populating it with parameters.

        Args:
            classes (dict): A dictionary of class names to their properties and methods.
            instance (object): The instance of the class where the actions will be called.

        Returns:
            list: A list of dictionaries representing the parameter tree structure, now including indexed subsystems.
        """
        logger.debug(f"Generating parameter tree dictionary for {instance}")
        tree_dict = []

        for class_name, class_info in classes.items():
            logger.debug(f"Processing class: {class_name} with info: {class_info}")
            class_dict = {'name': class_name, 'type': 'group', 'children': []}

            # Debugging the detection of fetch_trace method
            if class_info.get('has_fetch_trace', False):
                logger.debug(f"'has_fetch_trace' found for class: {class_name}")
                def make_fetch_trace_callback(instance):
                    def callback():
                        trace_data = instance.fetch_trace()
                        # gui_reference.update_plot(trace_data) This was made up nonse this whole part.
                    return callback
                
                # Create the action with the callback specific to this instrument instance
                fetch_trace_action = {
                    'name': 'Fetch Trace',
                    'type': 'action',
                    'action': make_fetch_trace_callback(instance)
                }
                logger.debug(f"Added 'Fetch Trace' action for class: {class_name}")

            for prop in class_info.get('properties', []):
                # Direct handling of indexed subsystems
                if prop['type'] == 'build' and 'indices' in prop:
                    logger.debug(f"Found indexed subsystem in class {class_name} for property {prop['name']}")
                    for index in range(1, prop['indices'] + 1):  # Assuming 1-based indexing
                        indexed_group_name = f"{prop['name']} {index}"
                        logger.debug(f"Creating indexed group: {indexed_group_name}")

                        indexed_group = {
                            'name': indexed_group_name,
                            'type': 'group',
                            'children': []
                        }

                        # Populate each indexed group with parameters
                        for subprop in class_info.get('properties', []):
                            if subprop['type'] != 'build':  # Avoid recursive builds
                                logger.debug(f"Adding property {subprop['name']} to indexed group {indexed_group_name}")
                                param_dict = self._construct_param_dict(subprop, class_name, instance, prefix=indexed_group_name)
                                indexed_group['children'].append(param_dict)

                        class_dict['children'].append(indexed_group)
                        logger.debug(f"Completed indexed group {indexed_group_name}")
                else:
                    # Handling non-indexed properties as usual
                    # logger.debug(f"Processing non-indexed property {prop['name']} for class {class_name}")
                    param_dict = self._construct_param_dict(prop, class_name, instance)
                    if param_dict:
                        class_dict['children'].append(param_dict)
                        # logger.debug(f"Added property {prop['name']} to class {class_name}")

            tree_dict.append(class_dict)
        logger.debug("Completed parameter tree dictionary generation.")
        
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
        logger.debug(f"Visiting ClassDef: {node.name}")
        self.current_class_name = node.name
        properties = []
        methods = []
        has_fetch_trace = False

        for item in node.body:
            if isinstance(item, ast.Assign):
                prop_details = self.handle_assignment(item)
                if prop_details:
                    properties.append(prop_details)
            elif isinstance(item, ast.FunctionDef):
                methods.append(item.name)
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

    def handle_init_method(self, method_node):
        logger.debug(f"Handling __init__ method in class {self.current_class_name}.")
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
            # Check if the function called is 'build' directly or via attribute access
            if hasattr(assign_node.value.func, 'attr') and assign_node.value.func.attr == 'build':
                logger.debug("🎉 Found 'build' call directly within assignment.")
                self.extract_build_call_details(assign_node.value)
            elif hasattr(assign_node.value.func, 'id') and assign_node.value.func.id == 'build':
                logger.debug("🎉 Found 'build' call by ID within assignment.")
                self.extract_build_call_details(assign_node.value)
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

    # Extract build call details specifically designed for 'build' calls
    def extract_build_call_details(self, call_node):
        args = [self.get_ast_node_value(arg) for arg in call_node.args]
        logger.debug(f"🎯 Extracted 'args' from 'build' call: {args}")
        keywords = {kw.arg: self.get_ast_node_value(kw.value) for kw in call_node.keywords}
        
        # Prepare a details dictionary to return
        details = {
            'args': args,
            'keywords': keywords,
        }
        
        if 'indices' in keywords:
            logger.debug(f"🎯 Extracted 'indices' from 'build' call: {keywords['indices']}")
        else:
            logger.debug("🚫 'build' call without 'indices'.")
        
        return details

    def handle_build_call(self, call_node, subsystem_name):
        # Extract build call details using the modified method
        build_details = self.extract_build_call_details(call_node)
        
        # Access 'indices' from the returned details, default to 1 if not specified
        indices = build_details['keywords'].get('indices', 1)
        logger.debug(f"Handling build call for {subsystem_name}, indices: {indices}")
        
        # Update class info as indexed with extracted details
        if self.current_class_name and self.current_class_name in self.classes:
            class_info = self.classes[self.current_class_name]
            class_info['indexed'] = True
            class_info['indices'] = indices
            self.classes[self.current_class_name] = class_info  # Update class info

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