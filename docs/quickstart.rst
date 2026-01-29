Quickstart
==========

This guide shows you how to get started with M3S in two simple workflows:

1. **I know my grid system** - You want to use MGRS, Geohash, H3, etc. and generate cells
2. **Help me choose precision** - You need guidance on what precision level to use

Installation
------------

.. code-block:: bash

   uv pip install m3s
   # or: pip install m3s

Workflow 1: I Know My Grid System
----------------------------------

Use this workflow when you know which grid system you need (MGRS, Geohash, H3, etc.) and want to generate cells that intersect your geometry.

Generate MGRS Cells for a Region
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from m3s import GridBuilder
   import geopandas as gpd

   # Load your area of interest
   my_area = gpd.read_file("my_region.geojson")

   # Generate all MGRS cells at 100m precision
   result = (GridBuilder
       .for_system('mgrs')
       .with_precision(3)  # precision 3 = 100m grid
       .in_polygon(my_area)
       .execute())

   cells = result.to_geodataframe()
   print(f"Generated {len(cells)} MGRS cells")
   print(cells[['cell_id', 'utm']].head())

Generate Geohash Cell at a Point
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from m3s import GridBuilder

   # Get Geohash cell for New York City
   result = (GridBuilder
       .for_system('geohash')
       .with_precision(6)  # ~1.2km x 0.6km cells
       .at_point(40.7128, -74.0060)  # NYC coordinates
       .execute())

   cell = result.single
   print(f"Geohash: {cell.identifier}")
   print(f"Area: {cell.area_km2:.2f} km²")

Generate H3 Cells in a Bounding Box
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from m3s import GridBuilder

   # Generate H3 hexagons covering Manhattan
   result = (GridBuilder
       .for_system('h3')
       .with_precision(8)  # resolution 8 (~0.7km edge)
       .in_bbox(-74.02, 40.70, -73.93, 40.80)  # Manhattan bbox
       .execute())

   cells = result.to_geodataframe()
   print(f"Generated {len(cells)} H3 cells")

Workflow 2: Help Me Choose Precision
-------------------------------------

Use this workflow when you don't know what precision to use. M3S provides intelligent precision selection based on your needs.

Option A: Choose by Use Case
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pick from common use cases like 'neighborhood', 'city', 'country':

.. code-block:: python

   from m3s import GridBuilder, PrecisionSelector
   import geopandas as gpd

   my_area = gpd.read_file("my_region.geojson")

   # Select precision for neighborhood-scale analysis
   selector = PrecisionSelector('h3')
   rec = selector.for_use_case('neighborhood')

   result = (GridBuilder
       .for_system('h3')
       .with_auto_precision(rec)
       .in_polygon(my_area)
       .execute())

   print(f"Using precision {rec.precision} ({rec.explanation})")
   print(f"Confidence: {rec.confidence:.0%}")
   print(f"Generated {len(result)} cells")

Option B: Choose by Target Cell Area
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specify the desired cell area in km²:

.. code-block:: python

   from m3s import GridBuilder, PrecisionSelector

   # I want cells around 10 km² each
   selector = PrecisionSelector('mgrs')
   rec = selector.for_area(10.0)  # 10 km² target

   result = (GridBuilder
       .for_system('mgrs')
       .with_auto_precision(rec)
       .in_bbox(-74.1, 40.7, -74.0, 40.8)
       .execute())

   print(f"Using precision {rec.precision}")
   print(f"Target area: 10 km², actual: {rec.actual_area_km2:.2f} km²")
   print(f"Generated {len(result)} cells")

Option C: Choose by Target Cell Count
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Specify how many cells you want for your region:

.. code-block:: python

   from m3s import PrecisionSelector

   # I want about 50 cells to cover this region
   selector = PrecisionSelector('geohash')
   rec = selector.for_region_count(
       bounds=(-74.1, 40.7, -74.0, 40.8),
       target_count=50
   )

   print(f"Recommended precision: {rec.precision}")
   print(f"Expected cells: ~{rec.metadata.get('estimated_cells', 'N/A')}")

Common Grid Systems Quick Reference
------------------------------------

Here are typical precision values for popular grid systems:

.. list-table::
   :header-rows: 1
   :widths: 15 15 50

   * - Grid System
     - Precision Range
     - Example Sizes
   * - **MGRS**
     - 1-5
     - P1: 100km, P3: 100m, P5: 1m
   * - **Geohash**
     - 1-12
     - P5: ~5km, P7: ~150m, P10: ~1m
   * - **H3**
     - 0-15
     - P5: ~250km², P8: ~0.7km², P12: ~3m²
   * - **S2**
     - 0-30
     - P10: ~500km², P20: ~0.5km², P25: ~2m²
   * - **Quadkey**
     - 1-23
     - P10: ~1000km², P15: ~30km², P18: ~4km²
   * - **Slippy**
     - 0-20
     - P5: ~2500km², P10: ~78km², P15: ~2.4km²

See :doc:`grid_comparison` for detailed precision equivalences.

Next Steps
----------

* **Explore Examples**: Check out the :doc:`auto_examples/index` for visual examples with code
* **Choose Your Grid**: Read the :doc:`grid_comparison` guide to select the best grid system
* **API Reference**: See the complete :doc:`api` documentation for all features
* **Advanced Features**: Learn about grid conversion, relationship analysis, and multi-resolution operations in the examples
