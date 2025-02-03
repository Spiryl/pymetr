import os

def compile_rst_contents(docs_root, output_file='_rst_dump.txt'):
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


if __name__ == "__main__":
    docs_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'docs'))
    compile_rst_contents(docs_root)

