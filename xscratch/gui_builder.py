# gui_builder.py
import ast
import tkinter as tk
from tkinter import filedialog
from pathlib import Path
from enum import Enum, EnumMeta

class PropertyDetails:
    def __init__(self, name, widget_type, options=None):
        self.name = name
        self.widget_type = widget_type
        self.options = options

    def __repr__(self):
        return f"{self.name}: Widget Type = {self.widget_type}, Options = {self.options}"

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
        if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'id'):
            prop_func_id = node.value.func.id
            if prop_func_id in ['switch_property', 'select_property', 'value_property']:
                prop_name = node.targets[0].id
                
                # Determine widget type based on the function id
                widget_type = {
                    'switch_property': 'QCheckBox',
                    'select_property': 'QComboBox',
                    'value_property': 'QLineEdit'
                }[prop_func_id]
                
                # Handle options only for 'select_property'
                options = None
                if prop_func_id == 'select_property':
                    # Retrieve the second argument from the call, which should be the Enum class
                    if len(node.value.args) > 1:
                        enum_arg = node.value.args[1]
                        if isinstance(enum_arg, ast.Attribute) and isinstance(enum_arg.value, ast.Name):
                            # This assumes the Enum is defined elsewhere and is being referenced as ClassName.EnumName
                            options = enum_arg.attr
                        elif isinstance(enum_arg, ast.Name):
                            # This is for Enum directly passed as an argument
                            options = enum_arg.id
                        
                # Create a PropertyDetails instance for this property
                property_detail = PropertyDetails(prop_name, widget_type, options)
                properties.append(property_detail)
        return properties

    def get_ast_node_value(self, node):
        # Simplified for brevity. Extend to handle complex types as needed.
        if isinstance(node, ast.Name):
            return node.id
        return "Unknown"

def generate_gui_code(file_path, classes):
    # Assuming all classes are in the same module and file_path is the path to this module
    module_name = Path(file_path).stem  # Extracts the module name from the file path
    
    # File Imports
    code = "from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox, QCheckBox, QFormLayout\n"
    code += "from PySide6.QtWidgets import QMainWindow, QTabWidget, QApplication\n"
    code += "from PySide6.QtCore import Qt\n"
    code += "import logging\n"
    code += f"from pymetr.instrument import Instrument \n"
    code += f"from pymetr.dark_style import get_dark_palette \n"
    code += f"from pymetr.{module_name} import " + ", ".join(classes.keys()) + "\n"

    # Control Class definitions
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
        code += "        layout.addLayout(form_layout)\n\n"

        # Widget creation
        for prop in properties:
            code += f"        # '{prop.name}' Control Widget\n"
            widget_name = f"self.{prop.name}"
            if prop.widget_type == 'QComboBox':
                widget_name = f"self.{prop.name}_combo"
                code += f"        {widget_name} = QComboBox()\n"
                code += f"        {widget_name}.addItems([item.name for item in {class_name}.{prop.options}])\n"
            elif prop.widget_type == 'QLineEdit':
                widget_name += "_edit"
                code += f"        {widget_name} = QLineEdit()\n\n"
            elif prop.widget_type == 'QCheckBox':
                widget_name += "_check"
                code += f"        {widget_name} = QCheckBox()\n"
                code += f"        {widget_name}.setCheckable(True)\n"
            code += f"        form_layout.addRow(QLabel('   {prop.name.capitalize()}   '), {widget_name})\n\n"

        # Signal Connections
        code += "        self.connect_signals()\n\n"
        code += "    def connect_signals(self):\n"
        for prop in properties:
            widget_name = f"self.{prop.name}"
            if prop.widget_type == 'QComboBox':
                widget_name += "_combo"
                code += f"        {widget_name}.currentIndexChanged.connect(lambda: self.update_{prop.name}({widget_name}.currentText()))\n"
            elif prop.widget_type == 'QLineEdit':
                widget_name += "_edit"
                code += f"        {widget_name}.editingFinished.connect(lambda: self.update_{prop.name}({widget_name}.text()))\n"
            elif prop.widget_type == 'QCheckBox':
                widget_name += "_check"
                code += f"        {widget_name}.stateChanged.connect(lambda state: self.update_{prop.name}(state))\n"

        # Setters/Update Methods
        for prop in properties:
            widget_name_suffix = {
                'QComboBox': '_combo',
                'QLineEdit': '_edit',
                'QCheckBox': '_check'  # For boolean values
            }.get(prop.widget_type, '_edit')  # Default to QLineEdit for any unknown types

            widget_name = f"self.{prop.name}{widget_name_suffix}"

            # Generate the update method for each property
            code += f"\n    def update_{prop.name}(self, value):\n"
            
            if prop.widget_type == 'QComboBox':
                # Directly assign the selected item's text for QComboBox
                code += f"        self.instrument.{class_name.lower()}.{prop.name} = value\n"
            elif prop.widget_type == 'QLineEdit':
                # Directly use the text input for QLineEdit
                code += f"        self.instrument.{class_name.lower()}.{prop.name} = value\n"
            elif prop.widget_type == 'QCheckBox':
                # For QCheckBox, convert the state to '1' or '0' based on checked state
                # Assuming 'value' is the state of the checkbox (Qt.Checked or not)
                code += f"        converted_value = '1' if value else '0'\n"
                code += f"        self.instrument.{class_name.lower()}.{prop.name} = converted_value\n"

        # Getter/ Sync Methods
        code += "\n    def sync(self):\n"
        code += "        # Sync UI with current instrument state\n"
        for prop in properties:
            widget_name = f"self.{prop.name}"
            if prop.widget_type == 'QComboBox':
                widget_name += "_combo"
                code += f"        current_value = str(self.instrument.{class_name.lower()}.{prop.name})\n\n"
                code += f"        index = {widget_name}.findText(current_value, Qt.MatchContains)\n"
                code += f"        {widget_name}.setCurrentIndex(index)\n"
            elif prop.widget_type == 'QLineEdit':
                widget_name += "_edit"
                code += f"        current_text = str(self.instrument.{class_name.lower()}.{prop.name})\n\n"
                code += f"        {widget_name}.setText(current_text)\n"
            elif prop.widget_type == 'QCheckBox':
                widget_name += "_check"
                code += f"        current_state = self.instrument.{class_name.lower()}.{prop.name} == '1'\n\n"
                code += f"        {widget_name}.setChecked(current_state)\n"

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
    code += "    dark_palette = get_dark_palette()\n"
    code += "    app.setStyle(\"Fusion\")\n"
    code += "    app.setPalette(dark_palette)\n"
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
    
# Example of how to use generate_gui_code with class_properties from analyze_code_with_file_dialog()
if __name__ == '__main__':
    analysis_results = analyze_code_with_file_dialog()
    if analysis_results:
        gui_code = generate_gui_code(analysis_results['file_path'], analysis_results['classes'])
        
        # Extract the directory, name, and extension of the selected file
        selected_file_path = Path(analysis_results['file_path'])
        new_file_name = selected_file_path.stem + "_gui" + selected_file_path.suffix  # Adds '_gui' before the extension
        new_file_path = selected_file_path.parent / new_file_name  # Constructs the full new path
        
        # Save the GUI code to the new file path
        with open(new_file_path, 'w') as file:
            file.write(gui_code)
            
        print(f"GUI code has been saved to {new_file_path}")