import os

def generate_directory_tree(path, filename='_project-tree.txt', exclude=None):
    if exclude is None:
        exclude = ['__pycache__', '.git', 'build', 'venv']
    tree = [".. code-block:: text", ""]

    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if d not in exclude]
        level = root.replace(path, '').count(os.sep)
        indent = '│   ' * (level)
        if level == 0:
            tree.append(os.path.basename(root) + '/')
        else:
            tree.append(indent[:-4] + '├── ' + os.path.basename(root) + '/')
        subindent = '│   ' * (level + 1)
        for f in files:
            tree.append(subindent + '├── ' + f)
    
    tree_str = '\n'.join(tree)

    # Define the output file path relative to 'conf.py'
    output_filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(output_filepath, 'w', encoding='utf-8') as f:  # Specify UTF-8 encoding here
        f.write(tree_str)

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    generate_directory_tree(project_root, filename='_project-tree.txt', exclude=['__pycache__', '.git', 'build', 'venv', '_static', 'scratch'])
