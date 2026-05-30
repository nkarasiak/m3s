M3S: Multi Spatial Subdivision System
=====================================

.. raw:: html

   <div style="text-align: center; margin: 20px 0;">
       <h2 style="color: #336790; margin-bottom: 10px;">Unified Spatial Grid Systems for Python</h2>
       <p style="font-size: 1.2em; color: #666; margin-bottom: 30px;">
           A comprehensive toolkit for working with multiple spatial indexing systems
       </p>
   </div>

M3S (Multi Spatial Subdivision System) is a powerful Python library that provides an intuitive interface for working with 11 spatial grid systems including **H3**, **Geohash**, **S2**, **MGRS**, and more.

**New in v0.5.1**: Simplified API with direct grid access, universal geometry handling, and intelligent auto-precision selection. No instantiation required—just ``import m3s`` and start working!

**Also Available**: Advanced GridBuilder API with fluent interface and 5 intelligent precision selection strategies.

.. grid:: 3

   .. grid-item-card:: 🌍 Multi-Grid Support
      :class-header: bg-light

      Support for 10+ spatial grid systems including Geohash, MGRS, H3, S2, QuadKey, and more with a consistent API.

   .. grid-item-card:: ⚡ Performance Optimized
      :class-header: bg-light

      Built with performance in mind, offering threaded parallelism for large-scale spatial operations.

   .. grid-item-card:: 🔧 Easy Integration
      :class-header: bg-light

      Seamless integration with GeoPandas, Shapely, and the broader Python geospatial ecosystem.

Getting Started
===============

Installation
------------

Install M3S using uv (recommended):

.. code-block:: bash

   uv pip install m3s

Or using pip:

.. code-block:: bash

   pip install m3s

Quick Example - Simplified API (v0.5.1+)
-----------------------------------------

The easiest way to get started:

.. code-block:: python

   import m3s
   from shapely.geometry import Polygon

   # Direct grid access - no instantiation needed!  (lon, lat)
   cell = m3s.Geohash.from_geometry((-74.0060, 40.7128))
   print(f"Cell: {cell.id}, Area: {cell.area_km2:.2f} km²")

   # Works with any geometry type
   polygon = Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)])
   cells = m3s.H3.from_geometry(polygon)

   # Get neighbors
   neighbors = m3s.Geohash.neighbors(cell)

   # Convert to GeoDataFrame
   gdf = cells.to_gdf()

   # Convert between grid systems
   h3_cells = cells.to_h3()

   # Find optimal precision
   precision = m3s.H3.find_precision(polygon, method='auto')
   cells = m3s.H3.from_geometry(polygon, precision=precision)

Advanced Example - GridBuilder API
-----------------------------------

For complex workflows with method chaining:

.. code-block:: python

   from m3s import GridBuilder, PrecisionSelector

   # Intelligent precision selection
   selector = PrecisionSelector('h3')
   rec = selector.for_use_case('neighborhood')

   # Fluent query with method chaining
   result = (GridBuilder
       .for_system('h3')
       .with_auto_precision(rec)
       .at_point(-74.0060, 40.7128)  # NYC (lon, lat)
       .find_neighbors(depth=1)
       .execute())

   print(f"Found {len(result)} cells at precision {rec.precision}")

   # Type-safe result access
   gdf = result.to_geodataframe()

Multi-Grid Comparison
----------------------

Compare same location across multiple grid systems:

.. code-block:: python

   from m3s import MultiGridComparator

   comparator = MultiGridComparator([
       ('geohash', 5),
       ('h3', 7),
       ('s2', 10)
   ])

   results = comparator.query_all(-74.0060, 40.7128)
   for system, cell in results.items():
       print(f"{system}: {cell.identifier} ({cell.area_km2:.2f} km²)")

Supported Grid Systems
======================

M3S supports **11 spatial grid systems** with unified precision parameters:

.. list-table::
   :header-rows: 1
   :widths: 15 35 30 20

   * - Grid System
     - Description
     - Use Cases
     - Precision Range
   * - **H3**
     - Hexagonal hierarchical spatial index
     - Analytics, ride-sharing, logistics
     - 0-15
   * - **Geohash**
     - Base-32 string location encoding
     - Databases, simple indexing
     - 1-12
   * - **S2**
     - Google's spherical geometry library
     - Global applications, planetary-scale
     - 0-30
   * - **MGRS**
     - Military Grid Reference System
     - Military, surveying, precise reference
     - 1-6 (100km→1m)
   * - **Quadkey**
     - Microsoft Bing Maps tile system
     - Web mapping, tile services
     - 1-23
   * - **Slippy**
     - OpenStreetMap standard tiles
     - Web maps, tile servers, caching
     - 0-20
   * - **C-squares**
     - Marine data indexing
     - Oceanography, marine biology
     - 1-5
   * - **GARS**
     - Global Area Reference System
     - Military, area reference
     - 1-3
   * - **Maidenhead**
     - Amateur radio grid locator
     - Amateur radio, QSO logging
     - 1-6
   * - **Plus Codes**
     - Open Location Codes
     - Address replacement, geocoding
     - 2-15

Key Features
============

✨ **Simplified API (New!)**
   Direct grid access with ``m3s.H3``, ``m3s.Geohash``, etc. No instantiation needed—just import and use!

🌐 **Universal Geometry Handling**
   Single ``from_geometry()`` method accepts points, polygons, bounding boxes, and GeoDataFrames.

🎯 **Intelligent Precision Selection**
   Auto-select optimal precision with 5 strategies: minimize variance, fewer/more cells, balanced, or target count. Use case presets for common scenarios (building, neighborhood, city, etc.).

🔄 **Easy Grid Conversion**
   Convert between any grid systems with ``.to_h3()``, ``.to_geohash()``, ``.to_s2()``, etc.

📦 **Powerful Collections**
   ``GridCellCollection`` provides filtering, mapping, hierarchical operations, and easy exports.

🔗 **Fluent Builder Interface**
   Advanced ``GridBuilder`` API for complex workflows with method chaining.

📊 **Multi-Grid Comparison**
   Simultaneously analyze multiple grid systems and compare coverage patterns.

🚀 **High Performance**
   Optimized precision finding with fast path for large areas, caching, and lazy evaluation.

📈 **Scalable Operations**
   Memory-efficient streaming, threaded parallel processing, and adaptive chunking for large datasets.

🛠️ **GeoPandas Integration**
   Native support for GeoDataFrames with automatic CRS transformation and UTM zone detection.

🔙 **Full Backward Compatibility**
   Existing code continues to work—new API is additive, not breaking.

Documentation
=============

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   quickstart
   auto_examples/index

.. toctree::
   :maxdepth: 2
   :caption: Guides

   grid_comparison

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api
   changelog

Community & Support
===================

- 📚 **Documentation**: Complete API reference and examples
- 🐛 **Issue Tracker**: `GitHub Issues <https://github.com/nkarasiak/m3s/issues>`_
- 💬 **Discussions**: `GitHub Discussions <https://github.com/nkarasiak/m3s/discussions>`_
- 📧 **Contact**: Nicolas Karasiak

License
=======

M3S is released under the MIT License. See the `LICENSE <https://github.com/nkarasiak/m3s/blob/main/LICENSE>`_ file for details.

----

.. raw:: html

   <div style="text-align: center; margin: 40px 0 20px 0; padding: 20px; background: #f8f9fa; border-radius: 8px;">
       <p style="margin: 0; color: #666;">
           Made with ❤️ by the M3S team | 
           <a href="https://github.com/nkarasiak/m3s" style="text-decoration: none;">⭐ Star us on GitHub</a>
       </p>
   </div>
