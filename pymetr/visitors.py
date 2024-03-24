import ast
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
from copy import deepcopy
import ast

class InstrumentVisitor(ast.NodeVisitor):
    """
    AST Node Visitor for instrument classes. It identifies instruments and subsystems,
    extracting relevant information and structuring it for further processing.

    Attributes:
        instruments (dict): A dictionary holding information about each instrument identified.
        current_instrument (str or None): The name of the currently processed instrument.
    """
    def __init__(self):
        super().__init__()
        self.instruments = {}
        self.current_instrument = None
        logger.debug("🎼 InstrumentVisitor initialized 🎼")

    def visit_ClassDef(self, node):
        """
        Visits class definitions, identifying instrument and subsystem classes
        and extracting relevant information.
        """
        logger.debug(f"🏛 Visiting Class Definition: {node.name} 🏛")
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        if 'Instrument' in bases:
            self.current_instrument = node.name
            logger.debug(f"🎷 Found Instrument: {self.current_instrument} 🎷")
            self.instruments[node.name] = {
                'subsystems': {}, 
                'properties': [], 
                'methods': [],
                'action_parameters': {}
            }
            
            # New logic to identify action methods dynamically
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    logger.debug(f"🔍 Found method in {self.current_instrument}: {item.name} 🔍")
                    # You can add more logic here to filter specific methods as actions
                    if not item.name.startswith('_'):  # Example condition to filter methods
                        self.instruments[self.current_instrument]['methods'].append(item.name)
                        self.instruments[self.current_instrument]['action_parameters'][item.name] = True
            
            
        elif 'Subsystem' in bases and self.current_instrument:
            logger.debug(f"🔩 Found Subsystem: {node.name} within {self.current_instrument} 🔩")
            subsystem_visitor = SubsystemVisitor()
            subsystem_visitor.visit(node)
            subsystem_info = self.instruments[self.current_instrument]['subsystems'].get(node.name, {
                'properties': [],
                'methods': [],
                'instances': {}
            })

            if subsystem_info.get('needs_indexing', False):
                # Assuming 'indices' is the total number of instances to create
                for index in range(1, subsystem_info['indices'] + 1):
                    # Adjusting the approach to generate a descriptive and unique indexed name
                    logger.debug(f"📐 Indexing {index} in {node.name} 📐")
                    # Deepcopy ensures each instance has its own copy of properties and methods
                    subsystem_info['instances'][index] = deepcopy(subsystem_visitor.properties_methods)
            else:
                self.instruments[self.current_instrument]['subsystems'][node.name].update(subsystem_visitor.properties_methods)
            logger.debug(f"✨ Subsystem info updated for {node.name} in {self.current_instrument} ✨")
        super().generic_visit(node)

    def visit_Assign(self, node):
        """
        Visits assignment nodes to identify subsystem build configurations,
        particularly looking for the 'build' method call to initialize subsystems.
        """
        if self.current_instrument and isinstance(node.value, ast.Call) and getattr(node.value.func, 'attr', '') == 'build':
            logger.debug(f"🏗 Parsing build call in {self.current_instrument} 🏗")
            subsystem_class_name = node.value.func.value.id
            indices = next((self.get_ast_node_value(kw.value) for kw in node.value.keywords if kw.arg == 'indices'), 1)

            subsystem_info = {
                'indices': indices,
                'needs_indexing': indices > 1,
                'properties': [],
                'methods': [],
                'instances': {} if indices > 1 else None
            }
            self.instruments[self.current_instrument]['subsystems'][subsystem_class_name] = subsystem_info
            logger.debug(f"🛠 Subsystem {subsystem_class_name} initialized with indexing: {indices > 1} 🛠")
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
    """
    AST Node Visitor dedicated to subsystem classes within an instrument definition.
    It extracts property and method definitions from the AST, enriching them with additional details
    for later use in constructing a parameterized representation of each subsystem.
    
    Attributes:
        properties_methods (dict): A dictionary holding properties and methods extracted from the subsystem.
    """
    def __init__(self):
        super().__init__()
        self.properties_methods = {'properties': [], 'methods': []}
        logger.debug("🚀 Initialized SubsystemVisitor 🚀")

    def visit_Assign(self, node):
        """
        Visits assignment nodes within the AST, looking for property definitions to capture and process.
        """
        logger.debug(f"🔍 Visiting Assign Node: {ast.dump(node)} 🔍")
        if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id'):
            prop_func_id = node.value.func.id
            if prop_func_id in ['value_property', 'select_property', 'switch_property']:
                logger.debug(f"✨ Found a property: {prop_func_id} ✨")
                prop_details = self.parse_property_details(node.value, prop_func_id)
                if prop_details:
                    prop_name = node.targets[0].id
                    prop_details['name'] = prop_name
                    self.properties_methods['properties'].append(prop_details)
                    logger.debug(f"📝 Added property details for {prop_name}: {prop_details} 📝")
        super().generic_visit(node)

    def visit_FunctionDef(self, node):
        """
        Visits function definition nodes within the AST, capturing method names for later processing.
        """
        logger.debug(f"📜 Visiting FunctionDef Node: {node.name} 📜")
        self.properties_methods['methods'].append(node.name)
        logger.debug(f"📌 Added method: {node.name} 📌")
        super().generic_visit(node)

    def parse_property_details(self, call_node, prop_func_id):
        """
        Parses and returns the details of a property based on its AST node and identified type.
        
        Args:
            call_node (ast.Call): The AST node representing the property definition call.
            prop_func_id (str): The identified type of property (e.g., 'value_property').

        Returns:
            dict: A dictionary of property details, including type and potentially other attributes like choices or range.
        """
        logger.debug(f"🧐 Parsing property details for type: {prop_func_id} 🧐")
        details = {'type': prop_func_id}
        if prop_func_id == 'value_property':
            for kw in call_node.keywords:
                if kw.arg in ['type', 'range']:
                    details[kw.arg] = self.get_ast_node_value(kw.value)
                    logger.debug(f"🔧 Setting {kw.arg}: {details[kw.arg]} 🔧")
        elif prop_func_id == 'select_property':
            if len(call_node.args) > 1:
                choices_arg = call_node.args[1]
                if isinstance(choices_arg, ast.List):
                    details['choices'] = [self.get_ast_node_value(el) for el in choices_arg.elts]
                    logger.debug(f"🔄 Choices set for select_property: {details['choices']} 🔄")
        elif prop_func_id in ['switch_property', 'data_property']:
            logger.debug(f"⚙️ No additional processing needed for {prop_func_id} ⚙️")
        else:
            logger.warning(f"🚨 Unsupported property function: {prop_func_id} 🚨")

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
    print(visitor.instruments)