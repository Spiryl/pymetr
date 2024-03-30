import ast
import logging
logger = logging.getLogger(__name__)
from copy import deepcopy
import ast

class InstrumentVisitor(ast.NodeVisitor):
    def __init__(self):
        super().__init__()
        self.instruments = {}
        self.current_instrument = None
        self.current_subsystem = None
        logger.debug("🎼 InstrumentVisitor initialized 🎼")

    def visit_ClassDef(self, node):
        logger.debug(f"🏛 Visiting Class Definition: {node.name} 🏛")
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        if 'Instrument' in bases:
            self.current_instrument = node.name
            logger.debug(f"🎷 Found Instrument: {self.current_instrument} 🎷")
            self.instruments[node.name] = {
                'subsystems': {},
                'properties': [],
                'methods': {},  # Initialize methods as a dictionary
                'sources': []
            }
            self.extract_instrument_info(node)

        elif node.name == 'Sources' and self.current_instrument:
            logger.debug(f"🔍 Found Sources class in {self.current_instrument} 🔍")
            self.extract_sources_info(node)

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
                self.handle_indexed_subsystem(node, subsystem_info, subsystem_visitor.properties_methods)
            else:
                self.instruments[self.current_instrument]['subsystems'][node.name].update(subsystem_visitor.properties_methods)
            logger.debug(f"✨ Subsystem info updated for {node.name} in {self.current_instrument} ✨")

        super().generic_visit(node)

    def extract_instrument_info(self, node):
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                logger.debug(f"🔍 Found method in {self.current_instrument}: {item.name} 🔍")
                if not item.name.startswith('_'):
                    method_info = {
                        'args': [arg.arg for arg in item.args.args if arg.arg != 'self'],
                        'return': self.get_return_annotation(item),
                        'is_source_method': self.is_source_method(item)  # Check if the method uses @source_command decorator
                    }
                    self.instruments[self.current_instrument]['methods'][item.name] = method_info
            elif isinstance(item, ast.Assign):
                if isinstance(item.value, ast.Call) and isinstance(item.value.func, ast.Name) and item.value.func.id == 'Sources':
                    sources_list = self.get_ast_node_value(item.value.args[0])
                    self.instruments[self.current_instrument]['sources'] = sources_list

    def is_source_method(self, node):
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name) and decorator.func.id == 'source_command':
                return True
        return False

    def get_return_annotation(self, node):
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            elif isinstance(node.returns, ast.Attribute):
                return f"{node.returns.value.id}.{node.returns.attr}"
        return None

    def extract_sources_info(self, node):
        for item in node.body:
            if isinstance(item, ast.Assign):
                if isinstance(item.value, ast.List):
                    sources_list = [el.value for el in item.value.elts if isinstance(el, ast.Constant)]
                    self.instruments[self.current_instrument]['sources'] = sources_list

    def handle_indexed_subsystem(self, node, subsystem_info, properties_methods):
        for index in range(1, subsystem_info['indices'] + 1):
            logger.debug(f"📐 Indexing {index} in {node.name} 📐")
            instance_info = deepcopy(properties_methods)
            self.instruments[self.current_instrument]['subsystems'][node.name]['instances'][index] = instance_info

    def visit_Assign(self, node):
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
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return [self.get_ast_node_value(el) for el in node.elts]
        elif isinstance(node, ast.UnaryOp):
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
        self.current_subsystem = None
        logger.debug("🚀 Initialized SubsystemVisitor 🚀")

    def visit_ClassDef(self, node):
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        if 'Subsystem' in bases:
            self.current_subsystem = node.name
            logger.debug(f"🏛 Visiting Subsystem: {self.current_subsystem} 🏛")
        self.generic_visit(node)
        if self.current_subsystem == node.name:
            self.current_subsystem = None

    def visit_Assign(self, node):
        logger.debug(f"🔍 Visiting Assign Node: {ast.dump(node)} 🔍")
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            prop_class_name = node.value.func.id
            if prop_class_name in ['SelectProperty', 'ValueProperty', 'SwitchProperty', 'StringProperty', 'DataProperty']:
                logger.debug(f"✨ Found a property: {prop_class_name} ✨")
                prop_details = self.parse_property_details(node.value, prop_class_name)
                if prop_details:
                    prop_name = node.targets[0].id
                    prop_details['name'] = prop_name
                    if self.current_subsystem:
                        prop_details['subsystem'] = self.current_subsystem
                    self.properties_methods['properties'].append(prop_details)
                    logger.debug(f"📝 Added property details for {prop_name}: {prop_details} 📝")
        super().generic_visit(node)

    def parse_property_details(self, call_node, prop_class_name):
        logger.debug(f"🧐 Parsing property details for type: {prop_class_name} 🧐")
        details = {'type': prop_class_name}
        # Handle args for SelectProperty specifically
        if prop_class_name == 'SelectProperty':
            choices_arg = next((arg for arg in call_node.args if isinstance(arg, ast.List)), None)
            if choices_arg:
                details['choices'] = [self.get_ast_node_value(el) for el in choices_arg.elts]

        # Process keywords for all properties
        for keyword in call_node.keywords:
            key = keyword.arg
            if key == 'doc_str':
                details[key] = self.get_ast_node_value(keyword.value)
            elif key in ['type', 'units']:
                details[key] = self.get_ast_node_value(keyword.value)
            elif key == 'range':
                # Special handling for range to ensure it captures a tuple/list
                details[key] = [self.get_ast_node_value(limit) for limit in keyword.value.elts]
            elif key == 'choices':
                # This handles dynamic choices provided through keywords
                details[key] = [self.get_ast_node_value(choice) for choice in keyword.value.elts]

        return details

    def get_ast_node_value(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return [self.get_ast_node_value(el) for el in node.elts]
        elif isinstance(node, ast.UnaryOp):
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

            # Print sources
            print("├── Sources")
            for source in instrument_info['sources']:
                print(f"│   ├── {source}")

            # Print source methods
            print("├── Source Methods")
            for method_name, method_info in instrument_info['methods'].items():
                if method_info['is_source_method']:
                    args_str = ', '.join(method_info['args'])
                    return_str = f" -> {method_info['return']}" if method_info['return'] else ""
                    print(f"│   ├── {method_name}({args_str}){return_str}")

            # Print other methods
            print("├── Other Methods")
            for method_name, method_info in instrument_info['methods'].items():
                if not method_info['is_source_method']:
                    args_str = ', '.join(method_info['args'])
                    return_str = f" -> {method_info['return']}" if method_info['return'] else ""
                    print(f"│   ├── {method_name}({args_str}){return_str}")

            # Print subsystems and their properties
            subsystems = instrument_info['subsystems'].items()
            for subsystem_name, subsystem_info in subsystems:
                if 'instances' in subsystem_info and subsystem_info['instances']:
                    print(f"├── {subsystem_name}")
                    for instance_name, instance_info in subsystem_info['instances'].items():
                        print(f"│   ├── {instance_name}")
                        print_properties(instance_info['properties'], is_last=False)
                else:
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