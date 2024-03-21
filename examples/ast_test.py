import ast
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
        self.current_class_name = node.name
        class_info = {
            'properties': [],
            'methods': [],
            'indices': None, 
            'has_fetch_trace': False
        }
        self.classes[self.current_class_name] = class_info

        for item in node.body:
            if isinstance(item, ast.Assign):
                prop_details = self.handle_assignment(item)
                if prop_details:
                    self.classes[self.current_class_name]['properties'].append(prop_details)
            elif isinstance(item, ast.FunctionDef):
                self.classes[self.current_class_name]['methods'].append(item.name)
                if item.name == 'fetch_trace':
                    self.classes[self.current_class_name]['has_fetch_trace'] = True

    def visit_Assign(self, node):
        # Check if the value of the assignment is a call to 'build'
        if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'attr') and node.value.func.attr == 'build':
            class_name = node.value.func.value.id  # This gets us 'Channel'
            indices = None
            # Loop through keywords to find 'indices'
            for kw in node.value.keywords:
                if kw.arg == 'indices':
                    indices = kw.value.n  # Assuming it's a simple number for simplicity
            self.classes[class_name]['indices'] = indices
            logger.debug(f"Class '{class_name}' has {indices} indices.")
            # Here, you can associate 'indices' with 'class_name' in your data structure

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
        print(f"Completed parsing. Extracted classes: {list(parsed_classes.keys())}")
        for class_name, details in parsed_classes.items():
            properties_str = "\n".join([f"- {prop}" for prop in details.get('properties', [])])
            methods_str = "\n".join([f"- {method}" for method in details.get('methods', [])])
            indices_str = f"index count = {details['indices']}" if details.get('indices') else ""
            print(f"Class {class_name}: {indices_str}\nProperties:\n{properties_str}\nMethods:\n{methods_str}")

    path = 'pymetr/instruments/DSOX1204G.py'
    with open(path, 'r') as file:
        source = file.read()

    tree = ast.parse(source, filename=path)
    print(tree)
    visitor = PyMetrClassVisitor()
    print(visitor)
    visitor.visit(tree)

    generate_debug_output(visitor.classes)