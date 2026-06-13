M3S: Multi Spatial Subdivision System
=====================================

**Unified spatial grid systems for Python and JavaScript — one consistent API, one shared Rust/WASM core, across 12 indexing systems.**

:doc:`Examples <auto_examples/index>` · `GitHub <https://github.com/nkarasiak/m3s>`__

M3S (Multi Spatial Subdivision System) provides an intuitive interface for working with **13 spatial grid systems** including **H3**, **Geohash**, **S2**, **MGRS**, **A5**, and more — in **Python** and in **JavaScript** (via WASM). Both bindings call the same Rust core, so a cell encoded in one language decodes identically in the other.

M3S gives direct grid access, universal geometry handling, and intelligent auto-precision selection. No instantiation required: just ``import m3s`` and start working.

**Also Available**: Advanced GridBuilder API with fluent interface and 5 intelligent precision selection strategies.

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

Quick example
-------------

The easiest way to get started:

.. tab-set::

   .. tab-item:: Python

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

   .. tab-item:: JavaScript

      .. code-block:: javascript

         import * as m3s from "m3s";
         await m3s.ready();

         // Direct grid access — (lon, lat, precision)
         const cell = m3s.Geohash.fromPoint(-74.0060, 40.7128, 6);
         console.log(`Cell: ${cell.id}, Area: ${cell.areaKm2.toFixed(2)} km²`);

         // Cells across a bounding box  [minLon, minLat, maxLon, maxLat]
         const cells = m3s.H3.fromBbox([-74.1, 40.7, -73.9, 40.8], 8);

         // Get neighbors
         const neighbors = m3s.Geohash.neighbors(cell);
         console.log(`${cells.length} cells, ${neighbors.length} neighbors`);

      .. note::

         The JS build wraps the shared core. True polygon fill, ``find_precision``,
         GeoPandas export and cross-grid conversion are Python-only — see
         :doc:`javascript`.

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

M3S supports **13 spatial grid systems** with unified precision parameters:

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
   * - **EA-Quad**
     - Equal-area quadtree (power-of-two km cells)
     - Equal-area analysis, sampling
     - 0-20
   * - **rHEALPix**
     - Equal-area aperture-9 DGGS (OGC standard)
     - Equal-area analysis, scientific data cubes
     - 0-15
   * - **A5**
     - Pentagonal equal-area DGGS (dodecahedron)
     - Equal-area global tiling
     - 0-30

Key Features
============

⚡ **Direct grid access**
   Reach any grid with ``m3s.H3``, ``m3s.Geohash``, etc. No instantiation needed, just import and use.

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
   grid_picker
   javascript

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api
   js_api
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
