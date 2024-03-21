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
            self.instruments[node.name] = {'subsystems': {}, 'properties': [], 'methods': []}
        elif 'Subsystem' in bases and self.current_instrument:
            # Instantiate and run a SubsystemVisitor for this subsystem class.
            subsystem_visitor = SubsystemVisitor()
            subsystem_visitor.visit(node)
            # Include the returned properties and methods into the instrument's subsystem entry.
            self.instruments[self.current_instrument]['subsystems'][node.name] = subsystem_visitor.properties_methods
        super().generic_visit(node)  # Continue traversal.

    def visit_Assign(self, node):
        if self.current_instrument and isinstance(node.value, ast.Call) and getattr(node.value.func, 'attr', '') == 'build':
            subsystem_class_name = node.value.func.value.id
            indices = next((self.get_ast_node_value(kw.value) for kw in node.value.keywords if kw.arg == 'indices'), 1)
            
            if indices > 1:
                # Initialize a container for indexed subsystem instances
                self.instruments[self.current_instrument]['subsystems'][subsystem_class_name] = {
                    'indices': indices,
                    'instances': {}
                }
                for index in range(1, indices + 1):
                    indexed_name = f"{subsystem_class_name} {index}"
                    # Use a deepcopy of the properties_methods structure if each channel should have the same properties
                    self.instruments[self.current_instrument]['subsystems'][subsystem_class_name]['instances'][indexed_name] = deepcopy(subsystem_visitor.properties_methods)
            else:
                self.instruments[self.current_instrument]['subsystems'][subsystem_class_name] = {'properties': [], 'methods': []}

            logger.debug(f"🎉 Associated {subsystem_class_name} with {self.current_instrument}, indices: {indices}")
            
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
        # Initialize a structure to hold properties and methods found within a subsystem.
        self.properties_methods = {'properties': [], 'methods': []}

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id'):
            prop_func_id = node.value.func.id
            if prop_func_id in ['value_property', 'select_property', 'switch_property']:
                prop_name = node.targets[0].id  # Assuming the left-hand side of the assignment is always the property name.
                prop_details = self.parse_property_details(node.value, prop_func_id)
                if prop_details:
                    prop_details['name'] = prop_name  # Ensuring 'name' key is added.
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

        print(f"Constructed subsystem property details: {details}")
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
    
if __name__ == "__main__":

    def print_consolidated_view(instrument):
        for instrument_name, instrument_info in instrument.items():
            print(f"{instrument_name}/")
            subsystems = instrument_info['subsystems'].items()
            
            for subsystem_name, subsystem_info in subsystems:
                print(f"├── {subsystem_name}")
                if 'instances' in subsystem_info:  # Handle indexed subsystems like Channel
                    instances = subsystem_info['instances'].items()
                    for instance_name, instance_info in instances:
                        print(f"│   ├── {instance_name}")
                        print_properties(instance_info['properties'], True)
                else:
                    print_properties(subsystem_info['properties'], False)

    def print_indexed_subsystem(subsystem_name, subsystem_info, is_last_subsystem, is_last_instance):
        connector = "└── " if is_last_subsystem and is_last_instance else "├── "
        print(f"│   {connector}{subsystem_name}")
        print_properties(subsystem_info['properties'], not (is_last_subsystem and is_last_instance))

    def print_properties(properties, has_more_subsystems):
        for j, prop in enumerate(properties):
            is_last_property = j == len(properties) - 1
            prop_summary = format_property_summary(prop)
            connector = "└── " if is_last_property and not has_more_subsystems else "├── "
            indent = "    " if has_more_subsystems else "│   "
            print(f"{indent}{connector}{prop_summary}")

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
    
    path = 'pymetr/instruments/DSOX1204G.py'  # Update this path
    with open(path, 'r') as file:
        source = file.read()

    tree = ast.parse(source, filename=path)

    # Assuming PyMetrClassVisitor is your revised visitor class
    visitor = InstrumentVisitor()
    visitor.visit(tree)  # First pass to identify structure

    print_consolidated_view(visitor.instruments)
    # print(visitor.instruments)