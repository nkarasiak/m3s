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

html_theme = "pydata_sphinx_theme"

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

# Suppress warnings for unpickleable config values (e.g., sphinx_gallery_conf contains functions)
suppress_warnings = ["config.cache"]

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "shapely": ("https://shapely.readthedocs.io/en/stable/", None),
    "geopandas": ("https://geopandas.org/en/stable/", None),
}

# HTML theme options for PyData Sphinx Theme
html_theme_options = {
    # Logo and branding
    "logo": {
        "text": "M3S 🌍",
        "image_light": None,
        "image_dark": None,
    },

    # Header and navigation
    "header_links_before_dropdown": 4,
    "show_nav_level": 2,
    "show_toc_level": 2,

    # Footer
    "footer_start": ["copyright"],
    "footer_end": ["sphinx-version", "theme-version"],

    # GitHub integration
    "github_url": "https://github.com/nkarasiak/m3s",
    "use_edit_page_button": True,

    # Navigation bar
    "navbar_start": ["navbar-logo"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],

    # Sidebar
    "primary_sidebar_end": ["sidebar-ethical-ads"],
    "secondary_sidebar_items": ["page-toc", "sourcelink"],

    # Search
    "search_bar_text": "Search documentation...",

    # Analytics (uncomment if needed)
    # "analytics": {"google_analytics_id": "your-analytics-id"},

    # Color scheme
    "pygments_light_style": "default",
    "pygments_dark_style": "monokai",

    # External links
    "external_links": [
        {
            "url": "https://github.com/nkarasiak/m3s",
            "name": "GitHub",
        },
        {
            "url": "https://pypi.org/project/m3s/",
            "name": "PyPI",
        },
    ],

    # Icon links in navbar
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/nkarasiak/m3s",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/m3s/",
            "icon": "fa-brands fa-python",
        },
    ],
}

# Context for edit buttons
html_context = {
    "github_user": "nkarasiak",
    "github_repo": "m3s",
    "github_version": "main",
    "doc_path": "docs",
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
