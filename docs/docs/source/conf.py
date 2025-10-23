# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'PoseApp'
copyright = '2025, A Mohammed Musharaff'
author = 'A Mohammed Musharaff'
release = '0.10'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

import os
import sys

# Add the project src to Python path
sys.path.insert(0, os.path.abspath('../../../src'))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",      # Google/NumPy docstrings
    "sphinx.ext.viewcode",      # "View Source" links
    "myst_parser",              # Markdown support
    "sphinx_autodoc_typehints", # Nice type-hint formatting
    "sphinx.ext.autosectionlabel",
]

html_theme = "furo"  # clean, responsive theme

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "private-members": False,
    "show-inheritance": True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = False  # set True if you prefer NumPy style
napoleon_include_init_with_doc = True
napoleon_use_param = True
napoleon_use_rtype = True

autodoc_mock_imports = [
    "cv2",
    "PySide6",
    "numpy",           # only if needed; otherwise keep real numpy
    "mediapipe",
    "tflite_runtime",
]
