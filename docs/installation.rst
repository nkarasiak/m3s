Installation
============

Requirements
------------

M3S requires Python 3.8 or later and has the following dependencies:

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

For development, clone the repository and install with development dependencies:

.. code-block:: bash

   git clone https://github.com/nkarasiak/m3s.git
   cd m3s
   pip install -e ".[dev]"

This will install M3S in editable mode along with all development dependencies including:

* pytest for testing
* black for code formatting
* ruff for linting
* sphinx for documentation
* matplotlib for examples

Verify Installation
-------------------

To verify that M3S is installed correctly, run:

.. code-block:: python

   import m3s
   print(m3s.__version__)

   # Test basic functionality
   from m3s import H3Grid
   grid = H3Grid(resolution=7)
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