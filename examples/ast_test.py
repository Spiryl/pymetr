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
        self.instances = {}  

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
                    subsystem_name = node.name
                    # Fetch instance information stored previously
                    for instance_name, info in self.instruments[self.current_instrument].get('instances', {}).items():
                        if info['class'] == subsystem_name:
                            subsystem_visitor = SubsystemVisitor(instance_name, info['indices'])
                            subsystem_visitor.visit(node)
                        # Rest of your logic for handling indexed instances
                else:
                    # For non-indexed subsystems, just pass the instance name
                    subsystem_visitor = SubsystemVisitor(instance_name=subsystem_name)
                    subsystem_visitor.visit(node)
        super().generic_visit(node)  # Continue traversal.

    def visit_Assign(self, node):
        if self.current_instrument and isinstance(node.value, ast.Call) and node.value.func.attr == 'build':
            # Extract instance name (minus 'self.') and class name
            instance_name = node.targets[0].attr
            class_name = node.value.func.value.id
            
            # Default index handling
            index = None
            # Check for 'indices' argument in build call
            for kw in node.value.keywords:
                if kw.arg == 'indices':
                    index = self.get_ast_node_value(kw.value)  # Assuming this method extracts the value
            
            # Initialize subsystem details in the dictionary
            subsystem_key = f"{class_name}_{instance_name}"
            self.instruments[self.current_instrument]['subsystems'][subsystem_key] = {
                'class_name': class_name,
                'instance_name': instance_name,
                'index': index,
                'properties': [],
                'methods': []
            }
            
            # Now pass these details to SubsystemVisitor
            subsystem_visitor = SubsystemVisitor(class_name=class_name, instance_name=instance_name, index=index)
            subsystem_visitor.visit(node)
            
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
    def __init__(self, class_name, instance_name, index=None):
        super().__init__()
        self.class_name = class_name  # Class name of the subsystem
        self.instance_name = instance_name  # Instance name used in the instrument
        self.index = index  # Index of the subsystem instance, if applicable
        self.properties_methods = {'properties': [], 'methods': []}  # Store found properties and methods

    def visit_Assign(self, node):
        # Logic to handle assignments within a subsystem class, focusing on properties.
        if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id'):
            prop_func_id = node.value.func.id
            if prop_func_id in ['value_property', 'select_property', 'switch_property']:
                prop_details = self.parse_property_details(node.value, prop_func_id)
                if prop_details:
                    prop_name = node.targets[0].id
                    prop_details['name'] = prop_name
                    # Adjusting path based on index
                    prop_details['path'] = f"{self.instance_name}[{self.index}].{prop_name}" if self.index is not None else f"{self.instance_name}.{prop_name}"
                    self.properties_methods['properties'].append(prop_details)
        super().generic_visit(node)

    def visit_FunctionDef(self, node):
        # Here, you're capturing methods. This looks good.
        self.properties_methods['methods'].append(node.name)
        super().generic_visit(node)

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
            # Now we also print the path for each property, assuming 'path' is a key in prop
            path_display = f"Path: {prop.get('path', 'N/A')}" if 'path' in prop else ""
            print(f"{indent}├── {prop_summary} {path_display}")

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

    # def format_property_summary(prop):
    #     """Formats a property summary based on its type and details."""
    #     if prop['type'] == 'select_property':
    #         return f"{prop['name']} (list) [Choices: {', '.join(prop['choices'])}]"
    #     elif prop['type'] == 'switch_property':
    #         return f"{prop['name']} (bool)"
    #     elif prop['type'] in ['value_property', 'int', 'float']:
    #         prop_summary = f"{prop['name']} ({prop.get('value_type', prop['type'])})"
    #         if 'range' in prop:
    #             prop_summary += f" [Range: {prop['range'][0]} to {prop['range'][1]}]"
    #         return prop_summary
    #     return f"{prop['name']} ({prop['type']})"
    
    # def format_property_summary(prop):
    #     """Formats a property summary based on its type and details."""
    #     prop_type = prop.get('type')
    #     summary_parts = [f"{prop['name']} ({prop_type})"]
    #     if 'choices' in prop:
    #         choices_str = ", ".join(prop['choices'])
    #         summary_parts.append(f"[Choices: {choices_str}]")
    #     elif 'range' in prop:
    #         range_str = f"[Range: {prop['range'][0]} to {prop['range'][1]}]"
    #         summary_parts.append(range_str)
    #     return " ".join(summary_parts)

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
    # print(visitor.instruments)