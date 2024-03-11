import ast
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

class PropertyDetails:
    def __init__(self, name, widget_type, valid_values=None):
        self.name = name
        self.widget_type = widget_type
        self.valid_values = valid_values

    def __repr__(self):
        return f"{self.name}: Widget Type = {self.widget_type}, Valid Values = {self.valid_values}"

class ClassVisitor(ast.NodeVisitor):
    def __init__(self):
        self.classes = {}

    def visit_ClassDef(self, node):
        properties = []
        for body_item in node.body:
            if isinstance(body_item, ast.Assign):
                properties.extend(self.handle_assignment(body_item))
        if properties:
            self.classes[node.name] = properties
        self.generic_visit(node)

    def handle_assignment(self, node):
        properties = []
        # Assuming 'command_property' calls are assignments
        if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id') and node.value.func.id == 'command_property':
            prop_name = node.targets[0].id
            # Handle both positional and keyword arguments for valid_values
            valid_values = None
            if len(node.value.args) > 1:  # Checking the second positional argument
                valid_values = self.get_ast_node_value(node.value.args[1])
            else:  # Fallback to checking kwargs
                for kw in node.value.keywords:
                    if kw.arg == 'valid_values':
                        valid_values = self.get_ast_node_value(kw.value)
                        break
            widget_type = 'QComboBox' if valid_values is not None else 'QLineEdit'
            properties.append(PropertyDetails(prop_name, widget_type, valid_values))
        return properties

    def get_ast_node_value(self, node):
        if isinstance(node, ast.Constant) and node.value is None:
            return None
        elif isinstance(node, ast.Constant):
            return node.s
        elif isinstance(node, ast.Name):
            return node.id
        # Extend this method to handle other types as necessary
        return "Unknown"

    def get_constant(self, node):
        # Extracting constant values (strings, integers, enums, etc.)
        if isinstance(node, ast.Constant):
            return node.s
        elif isinstance(node, ast.Name):
            return node.id
        # Extend to handle other types as necessary
        return None

def analyze_code(source_code):
    tree = ast.parse(source_code)
    visitor = ClassVisitor()
    visitor.visit(tree)
    return visitor.classes

def analyze_code_with_file_dialog():
    root = tk.Tk()
    root.withdraw()  # Hides the main window
    filename = filedialog.askopenfilename()  # Opens dialog and returns file path
    if filename:
        with open(filename, 'r') as file:
            source_code = file.read()
        tree = ast.parse(source_code)
        visitor = ClassVisitor()
        visitor.visit(tree)
        return {'file_path': filename, 'classes': visitor.classes}
    else:
        return None
    
def generate_gui_code(file_path, classes):
    # Assuming all classes are in the same module and file_path is the path to this module
    module_name = Path(file_path).stem  # Extracts the module name from the file path

    
    code = "from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox, QFormLayout\n"
    code += "from PySide6.QtWidgets import QMainWindow, QTabWidget, QApplication\n\n"
    code += "from PySide6.QtCore import Qt\n"
    code += "import logging\n"
    code += f"from pymetr.instrument import Instrument \n"
    code += f"from pymetr.{module_name} import " + ", ".join(classes.keys()) + "\n"
    for class_name, properties in classes.items():
        code += f"\nclass {class_name}Control(QWidget):\n"
        code += "    def __init__(self, instrument, parent=None):\n"
        code += "        super().__init__(parent)\n"
        code += "        self.instrument = instrument\n"
        code += "        self.init_ui()\n"
        code += "        self.sync()\n\n"
        code += "    def init_ui(self):\n"
        code += "        layout = QVBoxLayout(self)\n"
        code += "        form_layout = QFormLayout()\n"
        code += "        layout.addLayout(form_layout)\n"

        for prop in properties:
            widget_name = f"self.{prop.name}_{'combobox' if prop.widget_type == 'QComboBox' else 'field'}"
            code += f"\n        # {class_name}.{prop.name} control widget\n"
            if prop.widget_type == 'QComboBox':
                enum_name = f"{prop.name.capitalize()}s"  # Capitalize the property name and add an 's' to get the Enum name
                class_enum_name = f"{class_name}.{enum_name}"  # Combine class name with the Enum name
                code += f"        {widget_name} = QComboBox()\n"
                code += f"        {widget_name}.addItems([item.name for item in {class_enum_name}])\n"
                code += f"        form_layout.addRow(QLabel('{prop.name.capitalize()}'), {widget_name})\n"
            else:
                code += f"        {widget_name} = QLineEdit()\n"
                code += f"        form_layout.addRow(QLabel('{prop.name.capitalize()}'), {widget_name})\n"

        code += "        self.connect_signals()\n\n"
        code += "    def connect_signals(self):\n"
        for prop in properties:
            widget_name = f"self.{prop.name}_{'combobox' if prop.widget_type == 'QComboBox' else 'field'}"
            if prop.widget_type == 'QComboBox':
                code += f"        {widget_name}.currentIndexChanged.connect(self.update_{prop.name})\n"
            else:
                code += f"        {widget_name}.editingFinished.connect(self.update_{prop.name})\n"

        # Update methods
        for prop in properties:
            widget_var = f"self.{prop.name}_{'combobox' if prop.widget_type == 'QComboBox' else 'field'}"
            code += f"\n    def update_{prop.name}(self):\n"
            if prop.widget_type == 'QComboBox':
                code += f"        self.instrument.{class_name.lower()}.{prop.name} = {widget_var}.currentText()\n"
            else:
                code += f"        self.instrument.{class_name.lower()}.{prop.name} = {widget_var}.text()\n"

        # Sync method
        code += "\n    def sync(self):\n"
        code += "        # Sync UI with current instrument state\n"
        for prop in properties:
            widget_name = f"self.{prop.name}_{'combobox' if prop.widget_type == 'QComboBox' else 'field'}"
            if prop.widget_type == 'QComboBox':
                code += f"        {widget_name}.findText(str(self.instrument.{class_name.lower()}.{prop.name}), Qt.MatchContains)\n"
            else:
                code += f"        {widget_name}.setText(str(self.instrument.{class_name.lower()}.{prop.name}))\n"

    # Dynamically instantiate subsystems in MyInstrument class
    code += "\nclass MyInstrument(Instrument):\n"
    code += "    def __init__(self, resource_string):\n"
    code += "        super().__init__(resource_string)\n"
    for class_name in classes.keys():
        code += f"        self.{class_name.lower()} = {class_name}(self)\n"

    # Main window class and application logic
    code += "\nif __name__ == \"__main__\":\n"
    code += "    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')\n"
    code += "    app = QApplication([])\n"
    code += "    main_win = QMainWindow()\n"
    code += "    tab_widget = QTabWidget()\n"
    code += "    main_win.setCentralWidget(tab_widget)\n"
    code += "    resource_string = Instrument.select_instrument('TCPIP?*::INSTR')\n"
    code += "    instr = MyInstrument(resource_string)\n"
    code += "    instr.open()\n"

    # Dynamically add tabs for each class
    for class_name in classes.keys():
        code += f"    {class_name.lower()}_tab = {class_name}Control(instr)\n"
        code += f"    tab_widget.addTab({class_name.lower()}_tab, \"{class_name}\")\n"

    # Finalize and show the main window
    code += "    main_win.show()\n"
    code += "    app.exec()\n"

    return code

# Example of how to use generate_gui_code with class_properties from analyze_code_with_file_dialog()
if __name__ == '__main__':
    analysis_results = analyze_code_with_file_dialog()
    if analysis_results:
        gui_code = generate_gui_code(analysis_results['file_path'], analysis_results['classes'])
        with open('test_controls.py', 'w') as file:
            file.write(gui_code)
        print("GUI code has been saved to test_controls.py")
