M3S: Multi Spatial Subdivision System
=====================================

.. raw:: html

   <div style="text-align: center; margin: 20px 0;">
       <h2 style="color: #336790; margin-bottom: 10px;">Unified Spatial Grid Systems for Python</h2>
       <p style="font-size: 1.2em; color: #666; margin-bottom: 30px;">
           A comprehensive toolkit for working with multiple spatial indexing systems
       </p>
   </div>

M3S (Multi Spatial Subdivision System) is a powerful Python library that provides a modern fluent interface with intelligent precision selection for 12 spatial grid systems including **H3**, **Geohash**, **S2**, **MGRS**, **A5**, and more.

**New in v0.6.0**: Complete API redesign with fluent builder interface, 5 intelligent precision selection strategies, and unified parameters across all grid systems.

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

Quick Example (v0.6.0+)
-----------------------

Get started with the modern fluent API:

.. code-block:: python

   from m3s import GridBuilder, PrecisionSelector

   # Intelligent precision selection
   selector = PrecisionSelector('h3')
   rec = selector.for_use_case('neighborhood')

   # Fluent query with method chaining
   result = (GridBuilder
       .for_system('h3')
       .with_auto_precision(rec)
       .at_point(40.7128, -74.0060)  # NYC
       .find_neighbors(depth=1)
       .execute())

   print(f"Found {len(result)} cells at precision {rec.precision}")
   print(f"Confidence: {rec.confidence:.0%}")

   # Type-safe result access
   cell = result.single
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

   results = comparator.query_all(40.7128, -74.0060)
   for system, cell in results.items():
       print(f"{system}: {cell.identifier} ({cell.area_km2:.2f} km²)")

Supported Grid Systems
======================

M3S supports **12 spatial grid systems** with unified precision parameters:

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
   * - **A5**
     - Pentagonal DGGS (dodecahedral)
     - Climate modeling, global analysis
     - 0-30
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
   * - **What3Words**
     - 3-meter precision squares
     - Precise location reference
     - 1 (fixed)

Key Features
============

🎯 **Intelligent Precision Selection**
   5 strategies to auto-select optimal precision: area-based, count-based, use-case presets, distance-based, and performance-based.

🔗 **Fluent Builder Interface**
   Method chaining for elegant, readable workflows - compose queries with `.for_system().with_precision().at_point().execute()`.

📊 **Multi-Grid Comparison**
   Simultaneously analyze multiple grid systems, compare coverage patterns, and find precision equivalence.

🎨 **Type-Safe Results**
   Explicit `.single`, `.many`, and `.to_geodataframe()` accessors eliminate type ambiguity.

🔧 **Unified Parameters**
   All 12 grid systems use consistent `precision` parameter (no more confusion between resolution/level/zoom).

🚀 **High Performance**
   Precomputed lookup tables, caching, and lazy evaluation.

📈 **Scalable Operations**
   Memory-efficient streaming, threaded parallel processing, and adaptive chunking for large datasets.

🛠️ **GeoPandas Integration**
   Native support for GeoDataFrames with automatic CRS transformation and UTM zone detection.

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
