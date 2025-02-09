import ast

from copy import deepcopy
import ast

from pymetr.core.logging import logger

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
        if any(base in ['Instrument', 'SCPIInstrument'] for base in bases):
            self.current_instrument = node.name
            logger.debug(f"🎷 Found Instrument: {self.current_instrument} 🎷")
            self.instruments[node.name] = {
                'subsystems': {},
                'properties': [],
                'methods': {},
                'gui_methods': {},
                'other_methods': {},
                'sources': []
            }
            self.extract_instrument_info(node)

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
            if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                self.extract_method_info(item)
            elif isinstance(item, ast.Assign):
                self.process_assignment(item)

    def extract_method_info(self, item):
        logger.debug(f"Found method in {self.current_instrument}: {item.name}")
        method_info = {
            'args': [arg.arg for arg in item.args.args if arg.arg != 'self'],
            'return': self.get_return_annotation(item),
            'is_gui_method': self.is_gui_method(item)
        }
        if method_info['is_gui_method']:
            self.instruments[self.current_instrument]['gui_methods'][item.name] = method_info
        else:
            self.instruments[self.current_instrument]['other_methods'][item.name] = method_info

    def is_gui_method(self, node):
        for decorator in node.decorator_list:
            if (isinstance(decorator, ast.Attribute) and
                isinstance(decorator.value, ast.Name) and
                decorator.value.id == 'Instrument' and
                decorator.attr == 'gui_command'):
                return True
        return False

    def process_assignment(self, item):
        if (isinstance(item.value, ast.Call) and
                isinstance(item.value.func, ast.Name) and
                item.value.func.id == 'Sources'):
            sources_list = self.get_ast_node_value(item.value.args[0])
            self.instruments[self.current_instrument]['sources'] = sources_list
            logger.debug(f"Captured Sources for {self.current_instrument}: {sources_list}")

    def get_return_annotation(self, node):
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            elif isinstance(node.returns, ast.Attribute):
                return f"{node.returns.value.id}.{node.returns.attr}"
        return None

    def handle_indexed_subsystem(self, node, subsystem_info, properties_methods):
        for index in range(1, subsystem_info['indices'] + 1):
            logger.debug(f"📐 Indexing {index} in {node.name} 📐")
            instance_info = deepcopy(properties_methods)
            self.instruments[self.current_instrument]['subsystems'][node.name]['instances'][index] = instance_info

    def visit_Assign(self, node):
        if self.current_instrument:
            if isinstance(node.value, ast.Call) and getattr(node.value.func, 'attr', '') == 'build':
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
            elif (isinstance(node.value, ast.Call) and
                isinstance(node.value.func, ast.Name) and
                node.value.func.id == 'Sources'):
                logger.debug(f"Found Sources initialization: {ast.dump(node.value)}")
                sources_list = []
                
                # Check for positional arguments
                if node.value.args:
                    sources_arg = node.value.args[0]
                    if isinstance(sources_arg, ast.List):
                        sources_list = [el.value for el in sources_arg.elts]
                
                # Check for keyword arguments
                sources_keyword = next((kw for kw in node.value.keywords if kw.arg == 'sources'), None)
                if sources_keyword and isinstance(sources_keyword.value, ast.List):
                    sources_list = [el.value for el in sources_keyword.value.elts]
                
                if sources_list:
                    self.instruments[self.current_instrument]['sources'] = sources_list
                    logger.debug(f"Captured Sources for {self.current_instrument}: {sources_list}")
                else:
                    logger.warning(f"No sources found in Sources initialization for {self.current_instrument}")
        
        super().generic_visit(node)

    def get_ast_node_value(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.List):
            return [self.get_ast_node_value(el) for el in node.elts]
        elif isinstance(node, ast.Dict):
            return {key.value: self.get_ast_node_value(value) for key, value in zip(node.keys, node.values)}
        elif isinstance(node, ast.UnaryOp):
            operand = self.get_ast_node_value(node.operand)
            if isinstance(node.op, ast.UAdd):
                return +operand
            elif isinstance(node.op, ast.USub):
                return -operand
        else:
            logger.error(f"Unhandled node type: {type(node).__name__}")
            logger.debug(f"Node dump: {ast.dump(node)}")
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
                prop_name = node.targets[0].id
                prop_details = self.parse_property_details(node.value, prop_class_name, prop_name)
                if prop_details:
                    if self.current_subsystem:
                        prop_details['subsystem'] = self.current_subsystem
                    self.properties_methods['properties'].append(prop_details)
                    logger.debug(f"📝 Added property details for {prop_name}: {prop_details} 📝")
        super().generic_visit(node)

    def parse_property_details(self, call_node, prop_class_name, prop_name):
        logger.debug(f"🧐 Parsing property details for type: {prop_class_name} 🧐")
        details = {'type': prop_class_name, 'name': prop_name}
        
        for kw in call_node.keywords:
            if kw.arg == 'access':
                details['access'] = self.get_ast_node_value(kw.value)
                logger.debug(f"🔑 Access mode set for {prop_name}: {details['access']} 🔑")

        if prop_class_name == 'SelectProperty':
            if len(call_node.args) > 1:
                choices_arg = call_node.args[1]
                if isinstance(choices_arg, ast.List):
                    details['choices'] = [self.get_ast_node_value(el) for el in choices_arg.elts]
                    logger.debug(f"🔄 Choices set for SelectProperty: {details['choices']} 🔄")

        elif prop_class_name == 'ValueProperty':
            for kw in call_node.keywords:
                if kw.arg in ['type', 'range', 'units', 'doc_str']:
                    details[kw.arg] = self.get_ast_node_value(kw.value)
                    logger.debug(f"🔧 Setting {kw.arg}: {details[kw.arg]} 🔧")

        elif prop_class_name in ['SwitchProperty', 'StringProperty', 'DataProperty']:
            logger.debug(f"⚙️ No additional processing needed for {prop_class_name} ⚙️")

        else:
            logger.warning(f"🚨 Unsupported property class: {prop_class_name} 🚨")

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

            # Print GUI methods
            print("├── GUI Methods")
            for method_name, method_info in instrument_info['gui_methods'].items():
                args_str = ', '.join(method_info['args'])
                return_str = f" -> {method_info['return']}" if method_info['return'] else ""
                print(f"│   ├── {method_name}({args_str}){return_str}")

            # Print other methods
            print("├── Other Methods")
            for method_name, method_info in instrument_info['other_methods'].items():
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
            if isinstance(prop['choices'][0], str):
                choices_str = ", ".join(prop['choices'])
                summary_parts.append(f"[Choices: {choices_str}]")
            else:
                summary_parts.append(f"[Choices: {len(prop['choices'])} items]")
        elif 'range' in prop:
            range_str = f"[Range: {prop['range'][0]} to {prop['range'][1]}]"
            summary_parts.append(range_str)
        if 'units' in prop:
            summary_parts.append(f"[Units: {prop['units']}]")
        if 'access' in prop:
            summary_parts.append(f"[Access: {prop['access']}]")
        return " ".join(summary_parts)
    
    # Load a test driver
    path = 'scpi/drivers/DSOX1204G.py'  
    with open(path, 'r') as file:
        source = file.read()

    tree = ast.parse(source, filename=path)

    # Assuming scpiClassVisitor is your revised visitor class
    visitor = InstrumentVisitor()
    visitor.visit(tree)  # First pass to identify structure

    print_consolidated_view(visitor.instruments)
    #print(visitor.instruments)