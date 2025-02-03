import os

# Important Notes:
# Backup your project, especially the __init__.py files before running this script with the update function enabled.
# Review the init-master.txt file carefully after compiling and before updating the __init__.py files to ensure no unintended changes are made.
# This script assumes that the markers (# Start of and # End of) in init-master.txt remain intact and correctly reference each __init__.py file's path. Altering these markers or the file paths can lead to incorrect file updates.

def compile_init_contents(project_root, output_file='_init_dump.txt'):
    output_file = os.path.join(os.path.dirname(__file__), output_file)
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(project_root):
            if '__init__.py' in files:
                init_path = os.path.join(root, '__init__.py')
                outfile.write(f"# Start of {init_path}\n")
                with open(init_path, 'r', encoding='utf-8') as initfile:
                    outfile.write(initfile.read())
                outfile.write(f"\n# End of {init_path}\n\n")

def update_init_files(compiled_file='init-master.txt'):
    with open(compiled_file, 'r', encoding='utf-8') as infile:
        content = infile.read()

    sections = content.split('# End of ')
    for section in sections[:-1]:  # Skip the last empty split
        if "# Start of " in section:
            start_marker, file_contents = section.split('\n', 1)
            _, init_path = start_marker.split('# Start of ', 1)
            file_contents = file_contents.strip()  # Remove leading/trailing whitespace
            
            with open(init_path, 'w', encoding='utf-8') as outfile:
                outfile.write(file_contents)

if __name__ == "__main__":
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    compile_init_contents(project_root)
    # Uncomment the next line to enable writing back to __init__.py files
    # update_init_files()
