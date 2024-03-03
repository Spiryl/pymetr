import os
import sys

sys.path.insert(0, os.path.abspath('../'))

# -- Project information -----------------------------------------------------

project = 'Pymetr'
copyright = '2024, Ryan C. Smith'
author = 'Ryan C. Smith'
release = '3/01/2024'

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.graphviz',
    'sphinx.ext.intersphinx',
]

templates_path = ['_templates']
exclude_patterns = []

language = 'En'

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx-rtd-theme'
html_static_path = []

# -- GraphViz configuration --------------------------------------------------

graphviz_output_format = 'png'