M3S: Multi Spatial Subdivision System
=====================================

Unified spatial grid systems for scientific Python.

M3S (Multi Spatial Subdivision System) provides a consistent interface across
multiple spatial indexing systems such as H3, S2, Geohash, MGRS, and QuadKey.
It is designed for data scientists who need reliable spatial features, clean
conversions, and reproducible geospatial analysis.

Quickstart
==========

.. code-block:: python

   import geopandas as gpd
   from shapely.geometry import Point
   from m3s import H3Grid, GeohashGrid

   gdf = gpd.GeoDataFrame(
       {
           "city": ["New York", "London", "Tokyo"],
           "geometry": [
               Point(-74.0060, 40.7128),
               Point(-0.1278, 51.5074),
               Point(139.6503, 35.6762),
           ],
       },
       crs="EPSG:4326",
   )

   h3_cells = H3Grid(precision=7).intersects(gdf)
   geohash_cells = GeohashGrid(precision=6).intersects(gdf)

   print(len(h3_cells), len(geohash_cells))

Why M3S
=======

- One API for multiple grids (H3, S2, Geohash, MGRS, QuadKey, and more).
- Built for GeoPandas and Shapely workflows.
- Easy conversion and consistent cell operations.
- Designed for large-scale analytics.

Supported grid systems
======================

.. list-table::
   :header-rows: 1
   :widths: 22 36 42

   * - Grid system
     - Best for
     - Typical use cases
   * - **H3**
     - Hexagonal indexing at global scale
     - Aggregations, mobility analytics, segmentation
   * - **S2**
     - Hierarchical spherical cells
     - Large-scale geospatial products
   * - **Geohash**
     - Compact string encodings
     - Caching, text-based lookup, indexing
   * - **MGRS**
     - Human-friendly coordinate references
     - Field operations, reporting, surveys
   * - **QuadKey**
     - Web tile addressing
     - Mapping tiles, imagery pipelines

Documentation
=============

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   grids
   auto_examples/index

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api
   changelog

Community
=========

- `GitHub Issues <https://github.com/nkarasiak/m3s/issues>`_
- `GitHub Discussions <https://github.com/nkarasiak/m3s/discussions>`_

