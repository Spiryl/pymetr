import sys
import re
from pathlib import Path
from PySide6.QtWidgets import QApplication, QFileDialog

def parse_properties(file_content):
    # Adjusted to accurately capture and process information about valid values
    class_pattern = re.compile(r'class (\w+)\(Subsystem\):')
    prop_pattern = re.compile(r'(\w+) = command_property\("([^"]*)", valid_values=(\w+)?, doc_str="([^"]*)"\)')

    classes = {}
    for class_match in class_pattern.finditer(file_content):
        class_name = class_match.group(1)
        class_props_start = class_match.end()
        next_class_match = class_pattern.search(file_content, class_props_start)
        class_props_end = next_class_match.start() if next_class_match else len(file_content)
        
        properties = prop_pattern.findall(file_content, class_props_start, class_props_end)
        classes[class_name] = [{'name': p[0], 'enum': p[2], 'doc_str': p[3], 'has_valid_values': bool(p[2])} for p in properties]
    
    return classes

def generate_gui_code(classes):
    code = "from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QComboBox, QFormLayout\n\n"
    for class_name, properties in classes.items():
        code += f"class {class_name}Control(QWidget):\n"
        code += "    def __init__(self, instr, parent=None):\n"
        code += "        super().__init__(parent)\n"
        code += "        self.instr = instr\n"
        code += "        layout = QVBoxLayout(self)\n"
        code += "        form_layout = QFormLayout()\n"
        
        for prop in properties:
            if prop['has_valid_values']:
                enum_name = f"{prop['name'].capitalize()}s"  # Adjust based on your Enum naming convention
                items_code = f"[item.name for item in {class_name}.{enum_name}]"
                widget_creation_code = f"self.{prop['name']} = QComboBox()\n"
                widget_creation_code += f"self.{prop['name']}.addItems({items_code})\n"
            else:
                widget_creation_code = f"self.{prop['name']} = QLineEdit()\n"
            code += widget_creation_code
            
             # Inside the loop where widgets are created in generate_gui_code
            if prop['has_valid_values']:
                signal_connection_code = f"self.{prop['name']}.currentIndexChanged.connect(self.update_{prop['name']})"
            else:
                signal_connection_code = f"self.{prop['name']}.editingFinished.connect(self.update_{prop['name']})"
            code += f"        {signal_connection_code}\n\n"
        
        code += "        layout.addLayout(form_layout)\n"
        code += "\n"

        # Later in the code, outside of the initial loop, add placeholders for update methods
        for prop in properties:
            code += f"    def update_{prop['name']}(self):\n"
            code += f"        # Update the instrument property based on the widget value\n"
            code += f"        value = self.{prop['name']}.currentText() if prop['has_valid_values'] else self.{prop['name']}.text()\n"
            code += f"        self.instr.{class_name.lower()}.{prop['name']} = value\n\n"

        # After generating update methods
        code += "    def sync(self):\n"
        code += "        # Sync GUI with current instrument settings\n"
        for prop in properties:
            if prop['has_valid_values']:
                code += f"        current_value = self.instr.{class_name.lower()}.{prop['name']}\n"
                code += f"        current_index = self.{prop['name']}.findText(current_value)\n"
                code += f"        self.{prop['name']}.setCurrentIndex(current_index)\n"
            else:
                code += f"        self.{prop['name']}.setText(str(self.instr.{class_name.lower()}.{prop['name']}))\n"

    return code

def main():
    app = QApplication(sys.argv)
    file_dialog = QFileDialog()
    input_path, _ = file_dialog.getOpenFileName(caption="Select Subsystems File", filter="Python Files (*.py)")
    if input_path:
        with open(input_path, 'r') as file:
            file_content = file.read()
        classes = parse_properties(file_content)
        gui_code = generate_gui_code(classes)
        output_path = Path(input_path).stem + "_controls.py"
        with open(output_path, 'w') as file:
            file.write(gui_code)
        print(f"Generated GUI file: {output_path}")

if __name__ == "__main__":
    main()
