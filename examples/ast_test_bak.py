import ast
import logging
import json

# Configure logging to output to the console.
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger(__name__)

class InstrumentVisitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.instrument = {}
        self.current_instrument = None

    def visit_ClassDef(self, node):
        # Assuming 'Instrument' and 'Subsystem' are directly named bases for simplicity.
        # You may need to adjust this based on actual inheritance checks.
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        if 'Instrument' in bases:
            previous_instrument = self.current_instrument  # Store the previous instrument
            self.current_instrument = node.name
            self.instrument[node.name] = {'subsystems': {}, 'properties': [], 'methods': []}
            super().generic_visit(node)  # Visit child nodes
            self.current_instrument = previous_instrument  # Restore the previous instrument
        else:
            super().generic_visit(node)  # Still visit child nodes, but don't change the instrument context.

    def visit_Assign(self, node):
        if self.current_instrument and isinstance(node.value, ast.Call) and getattr(node.value.func, 'attr', '') == 'build':
            subsystem_class_name = node.value.func.value.id
            # Correctly extract indices, handling ast.Constant and other node types.
            indices = next((self.get_ast_node_value(kw.value) for kw in node.value.keywords if kw.arg == 'indices'), 1)
            self.instrument[self.current_instrument]['subsystems'][subsystem_class_name] = {'indices': indices}
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
    def __init__(self, instrument):
        super().__init__()
        self.instrument = instrument
        self.current_instrument = None
        self.current_subsystem = None  # Track the current subsystem being parsed

    def visit_ClassDef(self, node):
        # Identify if the class is an Instrument or Subsystem based on some criteria.
        if 'Instrument' in [base.id for base in node.bases if isinstance(base, ast.Name)]:
            self.current_instrument = node.name
            self.current_subsystem = None  # Reset current subsystem when entering an instrument class
            self.instrument[node.name] = {'subsystems': {}, 'properties': [], 'methods': []}
        elif 'Subsystem' in [base.id for base in node.bases if isinstance(base, ast.Name)]:
            if self.current_instrument:  # Ensure we are within an instrument context
                self.current_subsystem = node.name
                # Initialize the subsystem within the current instrument
                self.instrument[self.current_instrument]['subsystems'][self.current_subsystem] = {'properties': [], 'methods': []}
        super().generic_visit(node)

    def visit_Assign(self, node):
        # Handle properties within subsystems
        if self.current_subsystem and isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id'):
            # This assumes properties are defined via specific function calls (e.g., value_property)
            prop_name = node.targets[0].id if isinstance(node.targets[0], ast.Name) else None
            if prop_name:
                prop_func_id = node.value.func.id
                prop_details = self.parse_property_details(node.value, prop_func_id)
                if prop_details:
                    prop_details['name'] = prop_name
                    # Add property details to the current subsystem's properties list
                    self.instrument[self.current_instrument]['subsystems'][self.current_subsystem]['properties'].append(prop_details)
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
            print(f"{instrument_name}/")  # Instrument name
            subsystems = list(instrument_info['subsystems'].items())
            for i, (subsystem_name, subsystem_info) in enumerate(subsystems):
                prefix = "├── " if i < len(subsystems) - 1 else "└── "
                print(f"{prefix}{subsystem_name}")  # Subsystem name

                # Check if the subsystem has indices (i.e., multiple instances like channels)
                if 'indices' in subsystem_info and subsystem_info['indices'] > 1:
                    for index in range(1, subsystem_info['indices'] + 1):
                        channel_prefix = "│   ├── " if index < subsystem_info['indices'] else "│   └── "
                        print(f"{channel_prefix}Channel {index}")  # Indexed subsystem instance

                        properties = subsystem_info['properties']
                        for j, prop in enumerate(properties):
                            prop_prefix = "│   │   ├── " if j < len(properties) - 1 else "│   │   └── "
                            prop_summary = format_property_summary(prop)
                            print(f"{prop_prefix}{prop_summary}")
                else:
                    # Non-indexed subsystem or single instance handling
                    properties = subsystem_info['properties']
                    for j, prop in enumerate(properties):
                        prop_prefix = "│   ├── " if j < len(properties) - 1 else "│   └── "
                        prop_summary = format_property_summary(prop)
                        print(f"{prop_prefix}{prop_summary}")

                if subsystem_info['methods']:
                    # Assume methods come after properties for simplicity
                    method_prefix = "│   ├── " if properties else "│   ├── "
                    print(f"{method_prefix}Methods: {', '.join(subsystem_info['methods'])}")

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

    path = 'pymetr/instruments/DSOX1204G.py'
    with open(path, 'r') as file:
        source = file.read()

    tree = ast.parse(source, filename=path)

    # First pass to build the instrument-subsystem scaffold
    instrument_visitor = InstrumentVisitor()
    instrument_visitor.visit(tree)
    
    # Second pass to enrich the scaffold with subsystem properties
    subsystem_visitor = SubsystemVisitor(instrument_visitor.instrument)
    subsystem_visitor.visit(tree)
    
    # Now, subsystem_visitor.instrument contains the enriched structure
    print_consolidated_view(subsystem_visitor.instrument)

    