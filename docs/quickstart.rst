Quickstart
==========

This guide shows you how to get started with M3S. Choose your workflow:

1. **Simplified API (Recommended)** - Easy, direct access to grid systems—no setup required
2. **GridBuilder API (Advanced)** - Fluent interface for complex workflows
3. **Help me choose precision** - Intelligent precision selection

Installation
------------

.. code-block:: bash

   uv pip install m3s
   # or: pip install m3s

Simplified API (Recommended)
-----------------------------

The easiest way to work with spatial grids. Direct access, no instantiation needed!

Get Cell at a Point
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import m3s

   # Get cell at New York City
   cell = m3s.Geohash.from_geometry((40.7128, -74.0060))
   print(f"Cell: {cell.id}")
   print(f"Area: {cell.area_km2:.2f} km²")
   print(f"Centroid: {cell.centroid}")

   # Works with all 12 grid systems!
   h3_cell = m3s.H3.from_geometry((40.7128, -74.0060))
   mgrs_cell = m3s.MGRS.from_geometry((40.7128, -74.0060))
   a5_cell = m3s.A5.from_geometry((40.7128, -74.0060))

Generate Cells for an Area
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import m3s
   from shapely.geometry import Polygon
   import geopandas as gpd

   # Create a polygon
   polygon = Polygon([
       (-74.1, 40.7), (-73.9, 40.7),
       (-73.9, 40.8), (-74.1, 40.8)
   ])

   # Get cells (uses sensible default precision)
   cells = m3s.H3.from_geometry(polygon)
   print(f"Found {len(cells)} cells")

   # Convert to GeoDataFrame
   gdf = cells.to_gdf()

   # Or from GeoDataFrame
   my_gdf = gpd.read_file("my_region.geojson")
   cells = m3s.MGRS.from_geometry(my_gdf)

Get Neighbors
~~~~~~~~~~~~~

.. code-block:: python

   import m3s

   # Get cell
   cell = m3s.Geohash.from_geometry((40.7, -74.0))

   # Get neighbors (includes origin cell)
   neighbors = m3s.Geohash.neighbors(cell, depth=1)
   print(f"Found {len(neighbors)} neighbors")

   # Convert to GeoDataFrame for visualization
   gdf = neighbors.to_gdf()

Convert Between Grid Systems
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import m3s
   from shapely.geometry import box

   # Get H3 cells
   bbox = box(-74.1, 40.7, -73.9, 40.8)
   h3_cells = m3s.H3.from_geometry(bbox)

   # Convert to Geohash
   geohash_cells = h3_cells.to_geohash()

   # Convert to A5
   a5_cells = h3_cells.to_a5()

   print(f"H3: {len(h3_cells)} cells")
   print(f"Geohash: {len(geohash_cells)} cells")

Find Optimal Precision
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import m3s
   from shapely.geometry import Polygon

   polygon = Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)])

   # Find precision by method
   precision_auto = m3s.H3.find_precision(polygon, method='auto')  # Best quality
   precision_less = m3s.H3.find_precision(polygon, method='less')  # Fewer cells
   precision_more = m3s.H3.find_precision(polygon, method='more')  # More cells
   precision_100 = m3s.H3.find_precision(polygon, method=100)      # Target ~100 cells

   # Use the precision
   cells = m3s.H3.from_geometry(polygon, precision=precision_auto)

   # Or by use case
   precision = m3s.Geohash.find_precision_for_use_case('neighborhood')
   # Available: 'building', 'block', 'neighborhood', 'city', 'region', 'country'

   # Or by target area
   precision = m3s.H3.find_precision_for_area(target_km2=10.0)

Collection Operations
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import m3s
   from shapely.geometry import Polygon

   polygon = Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)])
   cells = m3s.H3.from_geometry(polygon)

   # Filter cells
   large_cells = cells.filter(lambda c: c.area_km2 > 10.0)

   # Map over cells
   areas = cells.map(lambda c: c.area_km2)

   # Get IDs
   ids = cells.to_ids()

   # Get polygons
   polygons = cells.to_polygons()

   # Total area
   total_area = cells.total_area_km2

   # Bounds
   min_lon, min_lat, max_lon, max_lat = cells.bounds

Available Grid Systems
~~~~~~~~~~~~~~~~~~~~~~

All 12 grid systems are directly accessible:

.. code-block:: python

   import m3s

   # Access any grid system
   m3s.A5           # Pentagonal DGGS
   m3s.Geohash      # Base32 spatial index
   m3s.H3           # Hexagonal grid
   m3s.MGRS         # Military Grid Reference
   m3s.S2           # Google's spherical geometry
   m3s.Quadkey      # Bing Maps tiles
   m3s.Slippy       # OpenStreetMap tiles
   m3s.CSquares     # Marine data indexing
   m3s.GARS         # Global Area Reference
   m3s.Maidenhead   # Amateur radio locator
   m3s.PlusCode     # Open Location Codes
   m3s.What3Words   # 3-meter precision squares

GridBuilder API (Advanced)
--------------------------

For complex workflows with method chaining, use the GridBuilder API.

Generate Cells with GridBuilder
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use this when you need advanced features like filtering, chaining, and transformations:

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

Advanced Precision Selection with PrecisionSelector
---------------------------------------------------

For detailed precision analysis, use the PrecisionSelector class.

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
