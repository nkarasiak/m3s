# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "M3S"
copyright = "2025, Nicolas Karasiak"
author = "Nicolas Karasiak"
release = "0.4.4"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.githubpages",
    "sphinx.ext.intersphinx",
    "sphinx_gallery.gen_gallery",
    "sphinx_design",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_material"

# Only add _static to path if it contains files (other than .gitkeep)
_static_dir = os.path.join(os.path.dirname(__file__), "_static")
_static_files = (
    [f for f in os.listdir(_static_dir) if not f.startswith(".") and f != ".gitkeep"]
    if os.path.exists(_static_dir)
    else []
)
html_static_path = ["_static"] if _static_files else []

# -- Extension configuration -------------------------------------------------

# Napoleon settings for Google/NumPy style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}

# Autosummary settings
autosummary_generate = True

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "shapely": ("https://shapely.readthedocs.io/en/stable/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
}

# HTML theme options for Sphinx Material
html_theme_options = {
    # Set the name of the project to appear in the navigation.
    'nav_title': 'M3S Documentation',
    
    # Set you GA account ID to enable tracking
    # 'google_analytics_account': 'your-analytics-id',
    
    # Specify a base_url used to generate sitemap.xml. If not
    # specified, then no sitemap will be built.
    'base_url': 'https://your-project-url.com/',
    
    # Set the color and the accent color
    'color_primary': 'blue',
    'color_accent': 'light-blue',
    
    # Set the repo location to get a badge with stats
    'repo_url': 'https://github.com/nkarasiak/m3s/',
    'repo_name': 'M3S',
    
    # Visible levels of the global TOC; -1 means unlimited
    'globaltoc_depth': 3,
    # If False, expand all TOC entries
    'globaltoc_collapse': False,
    # If True, show hidden TOC entries
    'globaltoc_includehidden': False,
    
    # Enable material design theme features
    'theme_color': 'blue',
    'master_doc': False,
    
    # Make the title clickable to go to homepage
    'logo_icon': '🌍',
    
    # Navigation bar style
    'nav_links': [
        {
            'href': 'index',
            'internal': True,
            'title': 'Home'
        },
        {
            'href': 'installation',
            'internal': True,
            'title': 'Installation'
        },
        {
            'href': 'auto_examples/index',
            'internal': True,
            'title': 'Gallery'
        },
        {
            'href': 'api',
            'internal': True,
            'title': 'API Reference'
        }
    ]
}

html_title = f"{project} v{release} Documentation"
html_short_title = project
html_logo = None
html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_css_files = []

# -- Sphinx Gallery configuration -------------------------------------------
try:
    from sphinx_gallery.sorting import NumberOfCodeLinesSortKey
    sorter = NumberOfCodeLinesSortKey
except ImportError:
    sorter = None

sphinx_gallery_conf = {
    'examples_dirs': '../examples',   # path to your example scripts
    'gallery_dirs': 'auto_examples',  # path to where to save gallery generated output
    'filename_pattern': r'.*\.py',     # pattern to identify example files
    'ignore_pattern': r'__init__\.py|parallel_processing_example\.py',
    'plot_gallery': True,             # whether to execute examples and create plots
    'download_all_examples': False,   # whether to create download links
    'first_notebook_cell': '%matplotlib inline',
    'remove_config_comments': True,
    'thumbnail_size': (200, 200),     # size of thumbnail images
}

if sorter:
    sphinx_gallery_conf['within_subsection_order'] = sorter
