Choosing a Grid
===============

This guide helps you choose the right spatial grid system for your use case.

Quick Decision Guide
--------------------

Need precise military coordinates?
   **MGRS** - UTM-based, 100km to 1m precision

Need uniform hexagons for analytics?
   **H3** - Perfect for ride-sharing, logistics, data aggregation

Need simple database indexing?
   **Geohash** - Fast, supported by Redis, MongoDB, Elasticsearch

Need web map tiles?
   **Quadkey** (Bing Maps) or **Slippy** (OpenStreetMap)

Need global spherical accuracy?
   **S2** - Google's planetary-scale system, or **A5** - pentagonal DGGS

Need marine data indexing?
   **C-squares** - International standard for oceanography

Grid System Comparison
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 12 12 15 15 46

   * - Grid System
     - Cell Shape
     - Precision Range
     - Typical Sizes
     - Primary Use Case
   * - **Geohash**
     - Rectangle
     - 1-12
     - P5: ~5km, P8: ~150m, P10: ~1m
     - Database indexing, proximity search, caching
   * - **H3**
     - Hexagon
     - 0-15
     - P5: ~250km², P8: ~0.7km², P12: ~3m²
     - Ride-sharing, analytics, uniform tessellation
   * - **S2**
     - Quadrilateral
     - 0-30
     - P10: ~500km², P20: ~0.5km², P25: ~2m²
     - Global apps, planetary-scale systems
   * - **MGRS**
     - Square (UTM)
     - 1-5
     - P1: 100km, P3: 100m, P5: 1m
     - Military, surveying, high-precision reference
   * - **Quadkey**
     - Square
     - 1-23
     - P10: ~1000km², P15: ~30km², P18: ~4km²
     - Bing Maps, web mapping, tile services
   * - **Slippy**
     - Square
     - 0-20
     - P5: ~2500km², P10: ~78km², P15: ~2.4km²
     - OpenStreetMap, web maps, tile servers
   * - **A5**
     - Pentagon
     - 0-15
     - P3: ~12000km², P7: ~47km², P10: ~0.4km²
     - Climate modeling, global analysis, DGGS
   * - **C-squares**
     - Rectangle
     - 1-5
     - P1: 100° (~12,000km²), P3: 1° (~123km²)
     - Marine biology, oceanography, fisheries
   * - **GARS**
     - Rectangle
     - 1-3
     - P1: 30' (~3000km²), P3: 5' (~28km²)
     - Military, area reference
   * - **Maidenhead**
     - Rectangle
     - 1-4
     - P1: 20°×10°, P2: 2°×1°, P3: ~5km²
     - Amateur radio, QSO logging
   * - **Plus Codes**
     - Rectangle
     - 2-15
     - P4: ~12m, P6: ~60cm
     - Address replacement, geocoding
   * - **What3Words**
     - Square
     - 1 (fixed)
     - 3m × 3m (fixed)
     - Precise location sharing, logistics

How to Choose
-------------

By Use Case
~~~~~~~~~~~

**Global Analysis**
   **S2** - Hierarchical quad-tree, works at all scales from global to centimeter

   **A5** - Pentagonal tessellation, no polar singularities, uniform globally

**Analytics & Data Science**
   **H3** - Hexagonal cells, uniform 6 neighbors, optimized for aggregation

   **Geohash** - Fast database indexing, proximity search, Z-order spatial indexing

**Web Mapping**
   **Quadkey** - Bing Maps standard, simple quad-tree addressing

   **Slippy** - OpenStreetMap tiles, universal (zoom, x, y) format

**Military & Surveying**
   **MGRS** - NATO standard, UTM-based accuracy, 100km to 1m

   **GARS** - Coarser area reference, 30' to 5' cells

**Marine & Environmental**
   **C-squares** - International standard for marine biological data

**Address Replacement**
   **Plus Codes** - Open-source, works anywhere, short codes for nearby locations

   **What3Words** - Human-readable 3-word addresses, fixed 3m precision

**Amateur Radio**
   **Maidenhead** - Ham radio standard, optimized for voice communication

By Cell Shape
~~~~~~~~~~~~~

**Hexagons**
   **H3** - Always 6 neighbors, uniform coverage, best for analytics

**Pentagons**
   **A5** - Global coverage without polar distortion

**Squares (UTM-based)**
   **MGRS** - Accurate distance/area calculations

**Squares (Web Mercator)**
   **Quadkey**, **Slippy** - Web mapping tiles

**Rectangles**
   **Geohash**, **C-squares**, **GARS**, **Maidenhead**, **Plus Codes**

**Spherical Quadrilaterals**
   **S2** - Google's spherical geometry

By Precision Needs
~~~~~~~~~~~~~~~~~~

**High Precision (meters)**
   **MGRS** (1m), **S2** (high levels), **H3** (res 12+), **What3Words** (3m fixed)

**Medium Precision (kilometers)**
   **H3**, **Geohash**, **Quadkey**, **S2**

**Coarse Precision (100+ km)**
   **MGRS** (P1), **C-squares** (P1), **GARS**

**Fixed Precision**
   **What3Words** - Always 3m × 3m

Examples
--------

Visual Comparisons
~~~~~~~~~~~~~~~~~~

See the Example Gallery for detailed visual comparisons:

* :doc:`auto_examples/grid_generation_example` - Compare how different grids tessellate the same area
* :doc:`auto_examples/precision_selection_example` - Learn intelligent precision selection
* :doc:`auto_examples/new_grids_example` - Explore C-squares, GARS, Maidenhead, Plus Codes
* :doc:`auto_examples/a5_example` - Understanding the A5 pentagonal grid
* :doc:`auto_examples/quadkey_s2_example` - Web mapping grid systems

Code Examples
~~~~~~~~~~~~~

Compare multiple grids for the same location:

.. code-block:: python

   from m3s import GridBuilder, PrecisionSelector

   # Compare same area with different grids
   for system in ['geohash', 'h3', 's2', 'mgrs']:
       selector = PrecisionSelector(system)
       rec = selector.for_use_case('neighborhood')

       result = (GridBuilder
           .for_system(system)
           .with_auto_precision(rec)
           .at_point(40.7128, -74.0060)
           .execute())

       cell = result.single
       print(f"{system:10s} P{rec.precision}: {cell.identifier} ({cell.area_km2:.2f} km²)")

Summary
-------

**Start Here:**

1. Read this guide to understand your options
2. Check the :doc:`quickstart` for basic usage
3. Explore the :doc:`auto_examples/index` for visual examples
4. See the :doc:`api` for complete documentation

**Still Unsure?**

* For most analytics tasks → **H3**
* For database indexing → **Geohash**
* For web mapping → **Slippy** or **Quadkey**
* For military/surveying → **MGRS**
* For global science → **S2** or **A5**

For more information on specific grid systems, see their official documentation:

* H3: https://h3geo.org/
* S2: https://s2geometry.io/
* Geohash: https://en.wikipedia.org/wiki/Geohash
* MGRS: https://en.wikipedia.org/wiki/Military_Grid_Reference_System
* Plus Codes: https://plus.codes/
