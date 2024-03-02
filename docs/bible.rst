Style Rules
==================

The guidelines below are the compass for our coding journey. Adhere to them, and the path to clean and readable code shall be illuminated.

Module Names
------------
- Lowercase with underscores as necessary to improve readability: `my_module.py`.

Package Names
-------------
- All lowercase, no underscores needed: `mypackage`.

Class Names
-----------
- CamelCase, capitalizing the first letter of each word: `MyClass`.

Function Names
--------------
- Lowercase with underscores separating words: `my_function()`.

Constant Names
--------------
- All caps with underscores separating words: `MY_CONSTANT`.

Variable Names
--------------
- Lowercase with underscores separating words: `my_variable`.

Indentation
-----------
- Use 4 spaces per indentation level. Consistency is key.

Line Length
-----------
- Keep each line to a maximum of 79 characters.

Imports
-------
- Group your imports in the following order: standard library imports, related third-party imports, local application/library specific imports. Add a blank line between each group.

Whitespace
----------
- Keep it clean—no trailing whitespace and use spacing around operators and after commas to improve readability.

File and Directory Naming
=========================

- **Files**: Use lowercase with underscores as necessary. For example, `my_script.py` or `my_module.py`.
- **Directories**: Use lowercase without underscores for package directories. For non-package directories, you can use underscores if it improves readability. For example, `mypackage` and `my_directory`.

Files should be named after the module they contain. A Python file called `my_module.py` would correspond to a module named `my_module`.

Directories that are Python packages (those containing an `__init__.py` file) should also be named in lowercase, without underscores, to align with package naming conventions. Non-package directories, such as those containing resources or documentation, can use underscores if it improves readability.

Remember, the goal is to keep names descriptive yet concise. They should give a clue about the content and purpose, without getting too lengthy.

Examples:
- Correct: `instrument/oscilloscope/controls/`
- Avoid: `Instrument/Oscilloscope_Controls/`

File Names
----------
- Use lowercase, and if it's a Python script, give it a `.py` extension. If the file is a module that will be imported, underscores can be used for readability: `useful_functions.py`.
- For executable scripts, keep it short and sweet, avoid underscores if possible: `manage`.

Directory Names
---------------
- Keep directory names lowercase and avoid using underscores unless it improves readability.
- Directories that are packages (i.e., contain an `__init__.py` file) should follow package naming conventions: `mypackage`.
- Non-package directories, like those for documentation, static files, or configuration, can use hyphens to improve readability: `config-files`, `static-assets`.