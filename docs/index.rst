M3S: Multi Spatial Subdivision System
=====================================

M3S (Multi Spatial Subdivision System) is a unified Python package for working with spatial grid systems including Geohash, MGRS (Military Grid Reference System), and H3 (Uber's Hexagonal Hierarchical Spatial Index).

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   auto_examples/index
   api
   examples
   changelog

Features
--------

* **Multiple Grid Systems**: Support for Geohash, MGRS, and H3 grid systems
* **Unified API**: Consistent interface across all grid systems
* **GeoDataFrame Integration**: Native support for GeoPandas GeoDataFrames
* **UTM Zone Detection**: Automatic UTM zone detection for accurate area calculations
* **Comprehensive Documentation**: Full API documentation with examples

Quick Start
-----------

Install M3S:

.. code-block:: bash

   pip install m3s

Basic usage:

.. code-block:: python

   import geopandas as gpd
   from shapely.geometry import Point
   from m3s import H3Grid, GeohashGrid, MGRSGrid

   # Create a sample GeoDataFrame
   gdf = gpd.GeoDataFrame({
       'name': ['New York', 'London'],
       'geometry': [Point(-74.0060, 40.7128), Point(-0.1278, 51.5074)]
   }, crs="EPSG:4326")

   # Generate H3 hexagonal grid
   h3_grid = H3Grid(resolution=8)
   h3_cells = h3_grid.intersects(gdf)

   # Generate Geohash grid
   geohash_grid = GeohashGrid(precision=6)
   geohash_cells = geohash_grid.intersects(gdf)

   # Generate MGRS grid
   mgrs_grid = MGRSGrid(precision=2)
   mgrs_cells = mgrs_grid.intersects(gdf)

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`