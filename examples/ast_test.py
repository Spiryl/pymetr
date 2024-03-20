import ast

class BuildCallVisitor(ast.NodeVisitor):
    def visit_Assign(self, node):
        # Check if the value of the assignment is a call to 'build'
        if isinstance(node.value, ast.Call) and hasattr(node.value.func, 'attr') and node.value.func.attr == 'build':
            class_name = node.value.func.value.id  # This gets us 'Channel'
            indices = None
            # Loop through keywords to find 'indices'
            for kw in node.value.keywords:
                if kw.arg == 'indices':
                    indices = kw.value.n  # Assuming it's a simple number for simplicity
            print(f"Class '{class_name}' has {indices} indices.")
            # Here, you can associate 'indices' with 'class_name' in your data structure

# Example code string
code = "self.channel = Channel.build(self, ':CHANnel', indices=4)"

# Parse the code into an AST
parsed_code = ast.parse(code)

# Create the visitor and walk through the AST
visitor = BuildCallVisitor()
visitor.visit(parsed_code)
