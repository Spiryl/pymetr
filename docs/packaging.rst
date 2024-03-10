====================================
Installing the PyMetr Package
====================================

The pymetr package is designed to simplify the creation of and interaction with test instrumentation using Python. This document outlines how to install the pymetr package, either for development purposes or for use in other projects.

Setup.py File
-------------

The `setup.py` file is the build script for setuptools. It tells setuptools about your package (such as the name and version) as well as which code files to include. An example `setup.py` file for pymetr might look like this:

.. code-block:: python

   from setuptools import setup, find_packages

   setup(
       name='pymetr',
       version='0.1.0',
       packages=find_packages(),
       description='Python Instrumentation Package',
       long_description=open('README.md').read(),
       author='Your Name',
       author_email='your.email@example.com',
       url='https://github.com/pymetr/pymetr',
       license='MIT',
       install_requires=[
           'numpy',
           'pyside6',
           'vispy',
           # Add other dependencies here
       ],
   )

This script is executed to install your package. The `find_packages()` function automatically discovers all packages and subpackages. In the `install_requires` list, you should specify any third-party dependencies your package needs.

Installing the Package
----------------------

There are two main scenarios for installing the pymetr package:

1. **Installing for Use in Projects**: If you wish to use pymetr as a dependency in other projects, you can install it from your local copy or from a Git repository.

   To install a local copy directly:

   .. code-block:: bash

      pip install path/to/pymetr

   Or, if your project is hosted on a Git repository, you can install it using:

   .. code-block:: bash

      pip install git+https://github.com/pymetr/pymetr.git

2. **Development Installation**: If you're developing pymetr and want to test changes as you make them, you should install the package in "editable" mode. This allows you to modify the source code and see those changes reflected without having to reinstall the package.

   Navigate to the root directory of your pymetr project and run:

   .. code-block:: bash

      pip install -e .

   This command tells pip to install the package in a way that's symlinked back to your source code, so changes are immediately effective.

Conclusion
----------

Installing the pymetr package is straightforward, whether for use in other projects or for development. The `setup.py` file is crucial for defining package metadata, dependencies, and more. For development purposes, installing in editable mode is highly recommended to facilitate testing and iteration.

For more information on packaging Python projects, refer to the official Python Packaging User Guide: https://packaging.python.org/tutorials/packaging-projects/
