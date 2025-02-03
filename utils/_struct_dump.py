#!/usr/bin/env python3
"""Minimal code structure crawler - outputs only essential class/method definitions."""

import os
import ast
import datetime
from pathlib import Path
from typing import List, Dict, Any

SKIP_DIRECTORIES = {'.git', '__pycache__', '.pytest_cache', 'venv', '.venv', 'build', 'docs', 'utils', 'xxx'}

class StructureVisitor(ast.NodeVisitor):
    def __init__(self):
        self.classes: List[Dict[str, Any]] = []
        self.functions: List[Dict[str, Any]] = []
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
            'args': self.get_minimal_args(node.args),
            'returns': self.get_returns(node)
        }
        if self.current_class:
            self.current_class['methods'].append(func_info)
        else:
            self.functions.append(func_info)

    def get_base_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name): return node.id
        elif isinstance(node, ast.Attribute): return f"{self.get_base_name(node.value)}.{node.attr}"
        return str(node)

    def get_minimal_args(self, args: ast.arguments) -> List[str]:
        arg_list = []
        for arg in args.args:
            if arg.arg == 'self': continue
            annotation = self.get_annotation(arg.annotation) if arg.annotation else ''
            arg_list.append(f"{arg.arg}: {annotation}" if annotation else arg.arg)
        if args.vararg: arg_list.append(f"*{args.vararg.arg}")
        if args.kwarg: arg_list.append(f"**{args.kwarg.arg}")
        return arg_list

    def get_returns(self, node: ast.FunctionDef) -> str:
        if node.returns: return self.get_annotation(node.returns)
        return ''

    def get_annotation(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name): return node.id
        elif isinstance(node, ast.Attribute): return f"{self.get_base_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript): return f"{self.get_base_name(node.value)}[{self.get_annotation(node.slice)}]"
        return str(node)

def struct_dump(start_path: str, output_file: str):
    start_path = Path(start_path).resolve()
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Minimal Code Structure - {datetime.datetime.now()}\n\n")
        
        for root, dirs, files in os.walk(start_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRECTORIES]
            current_path = Path(root)
            
            for filename in sorted(files):
                if not filename.endswith('.py'): continue
                filepath = current_path / filename
                rel_path = filepath.relative_to(start_path)
                
                try:
                    with open(filepath, 'r', encoding='utf-8') as source_file:
                        tree = ast.parse(source_file.read())
                    
                    visitor = StructureVisitor()
                    visitor.visit(tree)
                    
                    if visitor.classes or visitor.functions:
                        f.write(f"# {rel_path}\n")
                        
                        for cls in visitor.classes:
                            bases = f"({', '.join(cls['bases'])})" if cls['bases'] else ""
                            f.write(f"class {cls['name']}{bases}:")
                            if cls['methods']:
                                f.write("\n")
                                for method in cls['methods']:
                                    args = ', '.join(method['args'])
                                    returns = f" -> {method['returns']}" if method['returns'] else ''
                                    f.write(f"    def {method['name']}({args}){returns}\n")
                            else:
                                f.write(" pass\n")
                            f.write("\n")
                        
                        for func in visitor.functions:
                            args = ', '.join(func['args'])
                            returns = f" -> {func['returns']}" if func['returns'] else ''
                            f.write(f"def {func['name']}({args}){returns}\n")
                        
                        f.write("\n")
                        
                except Exception as e:
                    print(f"Error parsing {filepath}: {e}")

if __name__ == '__main__':
    struct_dump('.', 'utils/_struct_dump.txt')