#!/usr/bin/env python3
"""
Code crawler script to generate a single file containing all project source code.
Save this as 'collect_code.py' in your project's root directory.
"""

import os
import datetime
from pathlib import Path

# Configuration: List of directories to skip (relative to project root)
SKIP_DIRECTORIES = [
    '.git',
    '__pycache__',
    '.pytest_cache',
    'venv',
    '.venv',
    'build',
    'xxx',
    'docs',
    'utils',
    # Add more directories as needed
]

def collect_code(start_path, output_file, extensions=('.py', '.pyw')):
    """Crawl through directory and collect all source code files."""

    start_path = Path(start_path).resolve()

    def is_source_file(filename):
        """Check if file is a source code file we want to include."""
        return any(filename.endswith(ext) for ext in extensions)

    def should_skip_dir(current_path, dirname):
        """
        Check if the directory should be skipped based on the SKIP_DIRECTORIES list.

        Parameters:
            current_path (Path): The current directory being inspected.
            dirname (str): The name of the directory to potentially skip.

        Returns:
            bool: True if the directory should be skipped, False otherwise.
        """
        dir_path = (current_path / dirname).resolve()
        try:
            rel_dir_path = dir_path.relative_to(start_path)
        except ValueError:
            # The directory is not under start_path
            return False

        # Convert to POSIX style for consistency
        normalized_dir_path = rel_dir_path.as_posix()

        # Debug: Print the directory being checked
        print(f"Checking directory: {normalized_dir_path}")

        for skip_dir in SKIP_DIRECTORIES:
            if normalized_dir_path == skip_dir:
                print(f"--> Skipping directory (exact match): {normalized_dir_path}")
                return True
            if normalized_dir_path.startswith(skip_dir + '/'):
                print(f"--> Skipping directory (subdirectory of): {skip_dir}")
                return True
        return False

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write header
            f.write("# Project Source Code Collection\n")
            f.write(f"# Generated: {datetime.datetime.now()}\n")
            f.write(f"# Root Directory: {start_path}\n\n")

            # Walk through directory tree
            for root, dirs, files in os.walk(start_path, topdown=True):
                current_path = Path(root)

                # Make a copy of dirs to iterate over
                original_dirs = dirs.copy()

                # Iterate over a copy to safely modify the original list
                for dirname in original_dirs:
                    if should_skip_dir(current_path, dirname):
                        dirs.remove(dirname)  # Remove directory from traversal
                        skipped_dir_rel = (current_path / dirname).relative_to(start_path)
                        print(f"Skipping directory: {skipped_dir_rel.as_posix()}")

                # Process source files
                for filename in sorted(files):
                    if is_source_file(filename):
                        filepath = current_path / filename
                        rel_path = filepath.relative_to(start_path)

                        # Write file header
                        f.write(f"\n{'='*80}\n")
                        f.write(f"*** {filename} ***\n")
                        f.write(f"### {rel_path.as_posix()} ###\n")
                        f.write('='*80 + '\n\n')

                        # Write file contents
                        try:
                            with open(filepath, 'r', encoding='utf-8') as source_file:
                                content = source_file.read()
                                f.write(content)
                                f.write('\n\n')
                        except Exception as e:
                            f.write(f"ERROR reading file: {str(e)}\n\n")

            # Write footer
            f.write("\n" + "="*80 + "\n")
            f.write("# End of Project Source Code Collection\n")

        print(f"Source code collection complete. Output written to: {output_file}")

    except Exception as e:
        print(f"Error collecting source code: {str(e)}")

if __name__ == '__main__':
    # Configure these as needed
    PROJECT_ROOT = '.'  # Current directory
    OUTPUT_FILE = 'utils/_src_dump.txt'
    EXTENSIONS = ('.py', '.pyw')  # Add more extensions if needed

    collect_code(PROJECT_ROOT, OUTPUT_FILE, EXTENSIONS)
