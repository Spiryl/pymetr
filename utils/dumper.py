#!/usr/bin/env python3
"""
Integrated Dumper Tool

Features:
- Select a project directory.
- The left pane displays a file/directory tree with checkboxes.
  * Files and directories starting with '_' or '.' are skipped.
  * Only files with extensions: .py, .txt, .md, .yaml, and .toml appear.
  * Certain directories (e.g. "venv", "__pycache__", ".git", etc.) are skipped.
  * All items (files and directories) start checked.
- Dump Buttons:
    • Dump Source – concatenates the contents of all selected .py/.pyw files.
    • Dump Structure – uses AST to extract a minimal class/method structure.
    • Dump Tree – produces a text tree (with cool symbols) of the selected items.
    • Dump Init – concatenates all __init__.py files from the selected items.
- The output appears in the right pane.
- The selection logic allows you to deselect a top‑level node and then manually select a child subtree.
- After each dump, the total number of output lines is appended.
"""

import sys, os, ast, datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QFileDialog, QTextEdit, QTreeView, QLabel
)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt

# -----------------------------------------------------
# Global Filtering Settings and Helpers
# -----------------------------------------------------
ALLOWED_EXTENSIONS = {'.py', '.txt', '.md', '.yaml', '.toml'}
SKIP_DIRS = {'venv', '__pycache__', '.git', 'build', 'scratch', '_static'}

def is_allowed_file_name(file_name):
    """Return True if file_name does not start with '_' or '.' and has an allowed extension."""
    if file_name.startswith('_') or file_name.startswith('.'):
        return False
    ext = os.path.splitext(file_name)[1].lower()
    return ext in ALLOWED_EXTENSIONS

def is_allowed_directory_name(dir_name):
    """Return True if directory name does not start with '_' or '.' and is not in SKIP_DIRS."""
    if dir_name.startswith('_') or dir_name.startswith('.'):
        return False
    if dir_name.lower() in SKIP_DIRS:
        return False
    return True

def directory_contains_useable_files(directory):
    """
    Recursively checks if a directory contains at least one file with an allowed extension.
    Only walks allowed directories.
    """
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if is_allowed_directory_name(d)]
        for file in files:
            if is_allowed_file_name(file):
                return True
    return False

# -----------------------------------------------------
# File Collection and Dump Functions
# -----------------------------------------------------
def collect_files(path: str, extensions: tuple):
    """
    Recursively collect files under 'path' that have one of the specified extensions.
    Only files passing is_allowed_file_name() are returned.
    """
    collected = []
    if os.path.isfile(path):
        base = os.path.basename(path)
        if is_allowed_file_name(base) and path.endswith(extensions):
            collected.append(path)
    elif os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if is_allowed_directory_name(d)]
            for fname in files:
                if not is_allowed_file_name(fname):
                    continue
                if fname.endswith(extensions):
                    collected.append(os.path.join(root, fname))
    return collected

def dump_source(selected_paths):
    """
    Create a source dump by concatenating the contents of all .py/.pyw files
    from selected paths. Each file is wrapped with a header/footer.
    """
    extensions = ('.py', '.pyw')
    files = []
    for path in selected_paths:
        files.extend(collect_files(path, extensions))
    files = sorted(set(files))
    output_lines = []
    for f in files:
        output_lines.append(f"# Start of {f}")
        try:
            with open(f, 'r', encoding='utf-8') as file:
                output_lines.append(file.read())
        except Exception as e:
            output_lines.append(f"Error reading file: {e}")
        output_lines.append(f"# End of {f}\n")
    return "\n".join(output_lines)

class StructureVisitor(ast.NodeVisitor):
    """AST visitor for extracting minimal class/method structure."""
    def __init__(self):
        self.classes = []  # list of dicts
        self.functions = []  # list of module-level functions
        self.current_class = None

    def visit_ClassDef(self, node: ast.ClassDef):
        class_info = {
            'name': node.name,
            'bases': [self.get_base_name(base) for base in node.bases if self.get_base_name(base) != 'object'],
            'methods': []
        }
        old_class = self.current_class
        self.current_class = class_info
        self.classes.append(class_info)
        for item in node.body:
            self.visit(item)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name.startswith('_') and node.name != '__init__':
            return
        func_info = {
            'name': node.name,
            'args': [arg.arg for arg in node.args.args if arg.arg != 'self'],
            'returns': ""
        }
        if self.current_class:
            self.current_class['methods'].append(func_info)
        else:
            self.functions.append(func_info)

    def get_base_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self.get_base_name(node.value)}.{node.attr}"
        return str(node)

def dump_structure(selected_paths):
    """
    Create a structure dump by parsing each .py file and outputting a minimal
    class/method structure.
    """
    extensions = ('.py',)
    files = []
    for path in selected_paths:
        files.extend(collect_files(path, extensions))
    files = sorted(set(files))
    output_lines = []
    for f in files:
        output_lines.append(f"# {f}")
        try:
            with open(f, 'r', encoding='utf-8') as file:
                code = file.read()
            tree = ast.parse(code, filename=f)
            visitor = StructureVisitor()
            visitor.visit(tree)
            for cls in visitor.classes:
                bases = f"({', '.join(cls['bases'])})" if cls['bases'] else ""
                output_lines.append(f"class {cls['name']}{bases}:")
                if cls['methods']:
                    for method in cls['methods']:
                        args = ', '.join(method['args'])
                        output_lines.append(f"    def {method['name']}({args})")
                else:
                    output_lines.append("    pass")
                output_lines.append("")
            for func in visitor.functions:
                args = ', '.join(func['args'])
                output_lines.append(f"def {func['name']}({args})")
            output_lines.append("\n")
        except Exception as e:
            output_lines.append(f"Error parsing {f}: {e}\n")
    return "\n".join(output_lines)

def build_tree_lines(path, prefix=""):
    """
    Recursively build a list of strings representing the directory tree of 'path'
    using cool symbols. Only allowed files/directories are shown.
    """
    lines = []
    base = os.path.basename(path) if os.path.basename(path) else path
    if os.path.isdir(path):
        lines.append(prefix + base + "/")
        try:
            items = sorted(os.listdir(path))
        except PermissionError:
            lines.append(prefix + "    [Permission Denied]")
            return lines
        allowed_items = []
        for item in items:
            if item.startswith('_') or item.startswith('.'):
                continue
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                if not is_allowed_directory_name(item):
                    continue
                if not directory_contains_useable_files(full_path):
                    continue
                allowed_items.append(item)
            else:
                if not is_allowed_file_name(item):
                    continue
                allowed_items.append(item)
        count = len(allowed_items)
        for idx, item in enumerate(allowed_items):
            full_path = os.path.join(path, item)
            connector = "└── " if idx == count - 1 else "├── "
            new_prefix = prefix + ("    " if idx == count - 1 else "│   ")
            if os.path.isdir(full_path):
                lines.append(prefix + connector + item + "/")
                lines.extend(build_tree_lines(full_path, new_prefix))
            else:
                lines.append(prefix + connector + item)
    else:
        lines.append(prefix + base)
    return lines

def dump_tree(selected_paths):
    """
    Generate a text tree representation (with cool symbols) for the selected items.
    """
    output_lines = []
    for path in sorted(selected_paths):
        output_lines.extend(build_tree_lines(path))
        output_lines.append("")  # Blank line between trees
    return "\n".join(output_lines)

def dump_init(selected_paths):
    """
    Create an init dump by concatenating all __init__.py files from the selected paths.
    """
    init_files = []
    for path in selected_paths:
        if os.path.isfile(path) and os.path.basename(path) == '__init__.py':
            init_files.append(path)
        elif os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                dirs[:] = [d for d in dirs if is_allowed_directory_name(d)]
                for fname in files:
                    if fname == '__init__.py':
                        init_files.append(os.path.join(root, fname))
    init_files = sorted(set(init_files))
    output_lines = []
    for f in init_files:
        output_lines.append(f"# Start of {f}")
        try:
            with open(f, 'r', encoding='utf-8') as file:
                output_lines.append(file.read())
        except Exception as e:
            output_lines.append(f"Error reading file: {e}")
        output_lines.append(f"# End of {f}\n")
    return "\n".join(output_lines)

# -----------------------------------------------------
# New Selection Helper: Get selected items (files/directories)
# -----------------------------------------------------
def get_selected_items(model: QStandardItemModel):
    """
    Recursively traverse the tree and collect paths from items that are checked.
    
    If an item is checked and all its children are checked, we add the parent's path.
    Otherwise, we recursively traverse children so that manually checked nodes
    (even under an unchecked parent) are included.
    """
    selected = []
    
    def traverse(item):
        # If leaf, return the path if checked.
        if item.rowCount() == 0:
            if item.checkState() == Qt.Checked:
                return [item.data(Qt.UserRole)]
            else:
                return []
        children = [item.child(i) for i in range(item.rowCount())]
        all_children_checked = all(child.checkState() == Qt.Checked for child in children)
        if item.checkState() == Qt.Checked and all_children_checked:
            return [item.data(Qt.UserRole)]
        else:
            files = []
            for child in children:
                files.extend(traverse(child))
            return files
    
    for row in range(model.rowCount()):
        root_item = model.item(row)
        selected.extend(traverse(root_item))
    return list(set(selected))

# -----------------------------------------------------
# PySide6 UI Class
# -----------------------------------------------------
class DumperUI(QWidget):
    def __init__(self):
        super().__init__()
        self.project_root = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Integrated Dumper Tool")
        self.resize(1100, 700)
        mainLayout = QVBoxLayout(self)

        # --- Directory Selection ---
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel("No directory selected")
        self.dir_button = QPushButton("Select Project Directory")
        self.dir_button.clicked.connect(self.select_directory)
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(self.dir_button)
        mainLayout.addLayout(dir_layout)

        # --- Splitter: Left = Tree View, Right = Output ---
        splitter = QSplitter(Qt.Horizontal)
        self.treeView = QTreeView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Files/Directories"])
        self.treeView.setModel(self.model)
        self.model.itemChanged.connect(self.on_item_changed)
        splitter.addWidget(self.treeView)
        self.outputText = QTextEdit()
        splitter.addWidget(self.outputText)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        mainLayout.addWidget(splitter)

        # --- Dumper Buttons ---
        btn_layout = QHBoxLayout()
        self.dump_source_btn = QPushButton("Dump Source")
        self.dump_source_btn.clicked.connect(self.on_dump_source)
        self.dump_struct_btn = QPushButton("Dump Structure")
        self.dump_struct_btn.clicked.connect(self.on_dump_structure)
        self.dump_tree_btn = QPushButton("Dump Tree")
        self.dump_tree_btn.clicked.connect(self.on_dump_tree)
        self.dump_init_btn = QPushButton("Dump Init")
        self.dump_init_btn.clicked.connect(self.on_dump_init)
        btn_layout.addWidget(self.dump_source_btn)
        btn_layout.addWidget(self.dump_struct_btn)
        btn_layout.addWidget(self.dump_tree_btn)
        btn_layout.addWidget(self.dump_init_btn)
        mainLayout.addLayout(btn_layout)

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Project Directory", os.getcwd())
        if directory:
            self.project_root = directory
            self.dir_label.setText(directory)
            self.populate_tree()

    def populate_tree(self):
        """
        Build the QTreeView model from the selected project directory,
        applying our filtering rules.
        """
        self.model.removeRows(0, self.model.rowCount())
        root_item = self.create_item(self.project_root)
        self.model.appendRow(root_item)
        self.add_children(root_item, self.project_root)
        self.treeView.expandAll()

    def create_item(self, path):
        """
        Create a checkable QStandardItem for a file or directory.
        All items start checked.
        """
        name = os.path.basename(path) if os.path.basename(path) else path
        item = QStandardItem(name)
        item.setEditable(False)
        item.setCheckable(True)
        item.setCheckState(Qt.Checked)
        item.setData(path, Qt.UserRole)
        return item

    def add_children(self, parent_item, path):
        """
        Recursively add children for a directory, skipping items that are not allowed.
        """
        try:
            for entry in sorted(os.listdir(path)):
                if entry.startswith('_') or entry.startswith('.'):
                    continue
                full_path = os.path.join(path, entry)
                if os.path.isdir(full_path):
                    if not is_allowed_directory_name(entry):
                        continue
                    if not directory_contains_useable_files(full_path):
                        continue
                    child_item = self.create_item(full_path)
                    parent_item.appendRow(child_item)
                    self.add_children(child_item, full_path)
                else:
                    ext = os.path.splitext(entry)[1].lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        continue
                    child_item = self.create_item(full_path)
                    parent_item.appendRow(child_item)
        except PermissionError:
            pass

    def on_item_changed(self, item: QStandardItem):
        """
        Propagate check state changes to all children.
        """
        state = item.checkState()
        self.set_children_check_state(item, state)
        # Optional: force an immediate UI update:
        QApplication.processEvents()

    def set_children_check_state(self, item: QStandardItem, state):
        for row in range(item.rowCount()):
            child = item.child(row)
            child.setCheckState(state)
            self.set_children_check_state(child, state)

    def on_dump_source(self):
        selected = get_selected_items(self.model)
        if not selected:
            self.outputText.setText("No files selected.")
            return
        result = dump_source(selected)
        line_count = len(result.splitlines())
        result += f"\n\n-- Dump completed: {line_count} lines --"
        self.outputText.setText(result)

    def on_dump_structure(self):
        selected = get_selected_items(self.model)
        if not selected:
            self.outputText.setText("No files selected.")
            return
        result = dump_structure(selected)
        line_count = len(result.splitlines())
        result += f"\n\n-- Dump completed: {line_count} lines --"
        self.outputText.setText(result)

    def on_dump_tree(self):
        selected = get_selected_items(self.model)
        if not selected:
            self.outputText.setText("No files selected.")
            return
        result = dump_tree(selected)
        line_count = len(result.splitlines())
        result += f"\n\n-- Dump completed: {line_count} lines --"
        self.outputText.setText(result)

    def on_dump_init(self):
        selected = get_selected_items(self.model)
        if not selected:
            self.outputText.setText("No files selected.")
            return
        result = dump_init(selected)
        line_count = len(result.splitlines())
        result += f"\n\n-- Dump completed: {line_count} lines --"
        self.outputText.setText(result)

# -----------------------------------------------------
# Main Entry Point
# -----------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DumperUI()
    window.show()
    sys.exit(app.exec())
