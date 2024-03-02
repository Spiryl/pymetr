Rebuilding the Documentation
============================

This guide will walk you through setting up Sphinx for generating project documentation, installing Graphviz for creating diagrams, and using the Read the Docs theme for a clean, professional look.

Installing Sphinx
-----------------

To install Sphinx, you will need Python installed on your system. Python 3.6 or higher is recommended. You can install Sphinx using pip:

.. code-block:: bash

    pip install sphinx

Installing Graphviz
-------------------

Graphviz is an open-source graph visualization software used to create diagrams in Sphinx via the Graphviz extension. Install it from your operating system's package manager or the Graphviz download page:

- For Windows, download the installer from `Graphviz Download <https://graphviz.org/download/>`_.
- For macOS, use Homebrew:

  .. code-block:: bash

      brew install graphviz

- For Linux (Debian/Ubuntu):

  .. code-block:: bash

      sudo apt-get install graphviz

Installing Read the Docs Sphinx Theme
-------------------------------------

The Read the Docs theme can be installed via pip:

.. code-block:: bash

    pip install sphinx_rtd_theme

Installing Sphinx Graphviz Extension
------------------------------------

The Sphinx Graphviz extension should be included with Sphinx by default. If you need to install it separately, you can do so using pip:

.. code-block:: bash

    pip install sphinxcontrib-plantuml sphinxcontrib-actdiag sphinxcontrib-blockdiag sphinxcontrib-nwdiag sphinxcontrib-seqdiag

Setting Up `conf.py`
--------------------

Your `conf.py` file is where you configure your Sphinx documentation build. Here's a basic setup:

.. code-block:: python

    import os
    import sys
    sys.path.insert(0, os.path.abspath('../..'))  # Adjust the path to the root of your project

    project = 'Your Project'
    author = 'Your Name'

    extensions = [
        'sphinx.ext.autodoc',
        'sphinx.ext.graphviz',
        'sphinx_rtd_theme',
    ]

    html_theme = 'sphinx_rtd_theme'
    html_static_path = ['_static']

    graphviz_output_format = 'png'

Building Your Documentation
---------------------------

To build your documentation, navigate to your documentation directory and run:

.. code-block:: bash

    make html

This command will generate HTML documentation in the `_build/html` directory.

Creating Your First Page
------------------------

Start by creating an `index.rst` file in your documentation source directory with the following content:

.. code-block:: rst

    Welcome to My Project Documentation
    ===================================

    .. toctree::
       :maxdepth: 2
       :caption: Contents:

       introduction
       getting_started
       api_reference

Replace `introduction`, `getting_started`, and `api_reference` with the actual names of your `.rst` or `.md` files.

Adding Diagrams with Graphviz
-----------------------------

You can add diagrams to your `.rst` files using the Graphviz directive:

.. code-block:: rst

    .. graphviz::

       digraph example {
           A -> B;
           B -> C;
           C -> D;
       }

This simple directive will create a diagram showing nodes A, B, C, and D with directed edges between them as shown below.

.. graphviz::

       digraph example {
           A -> B;
           B -> C;
           C -> D;
       }

Conclusion
----------

You now have a basic Sphinx setup with support for Graphviz diagrams and a professional theme from Read the Docs. Modify the `conf.py` settings and `.rst` files to suit your project's documentation needs.
