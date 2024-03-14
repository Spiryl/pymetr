import ast
from pathlib import Path
from pyqtgraph.parametertree import Parameter
import logging

# Configure logging at the start of your script
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# TODO This is Subsystem Control Factory. Rename and adjust instrument_gui.
class GuiFactory:
    def __init__(self):
        pass  # No initialization required for now

    def _parse_source_file(self, path):
        """
        Parse the source file and return the classes dictionary from the visitor.
        """
        with open(path, "r") as source_file:
            tree = ast.parse(source_file.read(), filename=str(path))
        visitor = PyMetrClassVisitor()
        visitor.visit(tree)
        return visitor.classes

    def _construct_param_dict(self, prop, class_name):
        """
        Construct a parameter dictionary based on the property type.
        """
        param_dict = {}  # Initialize empty to be populated based on property type
        if prop['type'] == 'select_property':
            choices = prop.get('choices', [])
            param_dict = {
                'name': prop['name'],
                'type': 'list',
                'limits': choices,
                'value': choices[0] if choices else None,
            }
        elif prop['type'] == 'value_property':
            limits = prop.get('range', (None, None))
            limits = [None if v == 'Unknown' else v for v in limits]
            param_dict = {
                'name': prop.get('name'),
                'type': prop.get('value_type'),
                'limits': limits,
                'value': 0,  # Default value
            }
        elif prop['type'] == 'switch_property':
            param_dict = {
                'name': prop.get('name'),
                'type': 'bool',
                'value': False,  # Default value
            }
        # Handle other property types as needed...
        param_dict['doc'] = prop.get('doc_str', '')
        prop_path = f"{class_name}.{prop['name']}"
        param_dict['property_path'] = prop_path  # Add the property path for dynamic linkage
        return param_dict
    
    def generate_parameter_tree_dict(self, classes):
        """
        Generate a parameter tree dictionary from the classes dictionary.
        """
        tree_dict = []
        for class_name, class_info in classes.items():
            class_dict = {'name': class_name, 'type': 'group', 'children': []}
            for prop in class_info.get('properties', []):
                param_dict = self._construct_param_dict(prop, class_name)  # Pass class_name
                if param_dict:
                    class_dict['children'].append(param_dict)
            tree_dict.append(class_dict)
        return tree_dict

    def create_parameter_tree_from_file(self, path):
        """
        Create a parameter tree from a source file path.
        """
        classes = self._parse_source_file(path)  # This now correctly returns a dictionary of classes
        parameter_tree_dict = self.generate_parameter_tree_dict(classes)  # Pass this dictionary directly
        return Parameter.create(name='params', type='group', children=parameter_tree_dict)

import ast
import logging

class PyMetrClassVisitor(ast.NodeVisitor):
    def __init__(self):
        self.classes = {}

    def visit_ClassDef(self, node):
        # Determine if this class is a Subsystem by checking the base class names
        if any(base.id == 'Subsystem' for base in node.bases if isinstance(base, ast.Name)):
            properties = []
            for item in node.body:
                if isinstance(item, ast.Assign):
                    # Handle property assignments
                    prop_details = self.handle_assignment(item)
                    if prop_details:  # This check is crucial to avoid adding None
                        properties.append(prop_details)  # Only append if it's an actual property dict.
            
            # Only add the class to self.classes if it's a Subsystem
            if properties:
                self.classes[node.name] = {'properties': properties}

    def handle_assignment(self, node):
        if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id'):
            prop_func_id = node.value.func.id
            if prop_func_id in ['switch_property', 'select_property', 'value_property']:
                prop_name = node.targets[0].id
                prop_details = self.parse_property_details(node.value, prop_func_id)
                if prop_details:
                    prop_details['name'] = prop_name
                    # Adjust for select_property to include choices directly
                    if prop_func_id == 'select_property':
                        # Choices are the second argument in the call
                        choices_arg = node.value.args[1]
                        if isinstance(choices_arg, ast.List):
                            prop_details['choices'] = [self.get_ast_node_value(el) for el in choices_arg.elts]
                    return prop_details
        return None

    def parse_property_details(self, call_node, prop_func_id):
        details = {'type': prop_func_id}
        if prop_func_id == 'value_property':
            for kw in call_node.keywords:
                if kw.arg == 'type':
                    details['value_type'] = self.get_ast_node_value(kw.value)
                elif kw.arg == 'range':
                    range_values = [self.get_ast_node_value(el) for el in kw.value.elts]
                    details['range'] = range_values
        elif prop_func_id == 'select_property':
            if len(call_node.args) > 1:
                enum_arg = call_node.args[1]
                enum_name = self.get_ast_node_value(enum_arg)
                details['enum'] = enum_name
        elif prop_func_id == 'switch_property' or prop_func_id == 'data_property':
            # Handle accordingly, if needed
            pass
        return details

    def get_ast_node_value(self, node):
        if isinstance(node, ast.Str):  # Python 3.7 or earlier
            return node.s
        elif isinstance(node, ast.Constant):  # Python 3.8+
            return node.value
        elif isinstance(node, ast.Name):
            return node.id
        return "Unknown"

    
