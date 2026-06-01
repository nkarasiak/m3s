Installation
============

Requirements
------------

M3S requires Python 3.12 or later and has the following dependencies:

* **shapely** >= 2.0.0 - For geometric operations and polygon handling
* **pyproj** >= 3.4.0 - For coordinate system transformations (MGRS)
* **mgrs** >= 1.4.0 - For MGRS coordinate conversions
* **h3** >= 3.7.0 - For H3 hexagonal grid operations
* **geopandas** >= 0.13.0 - For spatial data manipulation

Install from PyPI
-----------------

The easiest way to install M3S is from PyPI using pip:

.. code-block:: bash

   pip install m3s

Install from Source
-------------------

You can also install M3S directly from the source repository:

.. code-block:: bash

   git clone https://github.com/nkarasiak/m3s.git
   cd m3s
   pip install .

Development Installation
------------------------

For development, M3S uses `uv <https://docs.astral.sh/uv/>`_ to manage a
reproducible environment. Clone the repository and run ``uv sync``:

.. code-block:: bash

   git clone https://github.com/nkarasiak/m3s.git
   cd m3s
   uv sync

This creates a ``.venv`` (interpreter pinned by ``.python-version``) from
``uv.lock`` and installs the default ``dev`` dependency group, giving a
complete dev setup. Run tooling with ``uv run`` (e.g. ``uv run pytest``).
The ``dev`` group includes:

* pytest / pytest-cov for testing
* black, isort, ruff, flake8 for formatting and linting
* mypy for type checking
* sphinx + sphinx-gallery (and matplotlib, contextily, folium) for the docs

Verify Installation
-------------------

To verify that M3S is installed correctly, run:

.. code-block:: python

   import m3s
   print(m3s.__version__)

   # Test basic functionality
   from m3s import H3Grid
   grid = H3Grid(precision=7)
   cell = grid.get_cell_from_point(40.7128, -74.0060)
   print(f"H3 cell: {cell.identifier}")

Optional Dependencies
---------------------

For visualization examples:

.. code-block:: bash

   pip install matplotlib

For testing:

.. code-block:: bash

   pip install pytest pytest-cov