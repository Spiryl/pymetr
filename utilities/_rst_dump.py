import os

def compile_rst_contents(docs_root, output_file='_rst_master.txt'):
    """
    Compiles the contents of all .rst files within the docs directory into a single file.

    Args:
        docs_root (str): The root directory of the documentation files.
        output_file (str): The name of the output file to write the compiled contents to.
    """
    output_file = os.path.join(docs_root, output_file)
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(docs_root):
            for file in files:
                if file.endswith(".rst"):
                    rst_path = os.path.join(root, file)
                    outfile.write(f"# Start of {rst_path}\n")
                    with open(rst_path, 'r', encoding='utf-8') as rstfile:
                        outfile.write(rstfile.read())
                    outfile.write(f"\n# End of {rst_path}\n\n")

# Uncomment and use this function with caution. 
# It's typically not necessary to write back to original .rst files in the same way as __init__.py files.
# def update_rst_files(compiled_file='_all-docs-combined.rst'):
#     with open(compiled_file, 'r', encoding='utf-8') as infile:
#         content = infile.read()
# 
#     sections = content.split('# End of ')
#     for section in sections[:-1]:  # Skip the last empty split
#         if "# Start of " in section:
#             start_marker, file_contents = section.split('\n', 1)
#             _, rst_path = start_marker.split('# Start of ', 1)
#             file_contents = file_contents.strip()  # Remove leading/trailing whitespace
#             
#             with open(rst_path, 'w', encoding='utf-8') as outfile:
#                 outfile.write(file_contents)

if __name__ == "__main__":
    docs_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs'))
    compile_rst_contents(docs_root)
    # Uncomment the next line to enable writing back to .rst files, but use with caution.
    # update_rst_files()
