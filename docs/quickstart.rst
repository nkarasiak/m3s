Quick Start Guide
=================

This guide will help you get started with M3S by showing basic usage patterns for each grid system.

Basic Grid Operations
---------------------

Creating Grid Instances
~~~~~~~~~~~~~~~~~~~~~~~~

Each grid system has its own class with specific precision parameters:

.. code-block:: python

   from m3s import H3Grid, GeohashGrid, MGRSGrid

   # H3 hexagonal grid (resolution 0-15)
   h3_grid = H3Grid(resolution=8)  # ~1.7km edge length

   # Geohash rectangular grid (precision 1-12)
   geohash_grid = GeohashGrid(precision=6)  # ~1.2km x 0.6km

   # MGRS square grid (precision 0-5)
   mgrs_grid = MGRSGrid(precision=2)  # 1km x 1km grid

Getting Cells from Points
~~~~~~~~~~~~~~~~~~~~~~~~~~

Convert latitude/longitude coordinates to grid cells:

.. code-block:: python

   # New York City coordinates
   lat, lon = 40.7128, -74.0060

   # Get cells for the same point in different grid systems
   h3_cell = h3_grid.get_cell_from_point(lat, lon)
   geohash_cell = geohash_grid.get_cell_from_point(lat, lon)
   mgrs_cell = mgrs_grid.get_cell_from_point(lat, lon)

   print(f"H3 cell: {h3_cell.identifier}")
   print(f"Geohash cell: {geohash_cell.identifier}")
   print(f"MGRS cell: {mgrs_cell.identifier}")

Working with GeoDataFrames
---------------------------

M3S integrates seamlessly with GeoPandas for spatial data analysis:

.. code-block:: python

   import geopandas as gpd
   from shapely.geometry import Point, box

   # Create a sample GeoDataFrame
   gdf = gpd.GeoDataFrame({
       'city': ['New York', 'London', 'Tokyo'],
       'population': [8_400_000, 9_000_000, 14_000_000],
       'geometry': [
           Point(-74.0060, 40.7128),   # NYC
           Point(-0.1278, 51.5074),    # London
           Point(139.6917, 35.6895),   # Tokyo
       ]
   }, crs="EPSG:4326")

   # Generate grid cells that intersect with the points
   h3_result = h3_grid.intersects(gdf)
   
   print(f"Generated {len(h3_result)} H3 cells")
   print(h3_result[['city', 'cell_id', 'utm']].head())

Polygon Intersections
~~~~~~~~~~~~~~~~~~~~~

Find grid cells that intersect with larger areas:

.. code-block:: python

   # Create a bounding box around Manhattan
   manhattan_bbox = box(-74.02, 40.70, -73.93, 40.80)
   manhattan_gdf = gpd.GeoDataFrame(
       {'name': ['Manhattan']}, 
       geometry=[manhattan_bbox], 
       crs="EPSG:4326"
   )

   # Find all grid cells that intersect Manhattan
   manhattan_cells = h3_grid.intersects(manhattan_gdf)
   print(f"Manhattan intersects {len(manhattan_cells)} H3 cells")

Grid System Comparison
----------------------

Different grid systems have different characteristics:

.. code-block:: python

   # Compare grid systems for the same area
   test_area = gpd.GeoDataFrame(
       {'name': ['Test Area']},
       geometry=[box(-74.1, 40.7, -74.0, 40.8)],
       crs="EPSG:4326"
   )

   # Generate cells with different grid systems
   h3_cells = H3Grid(resolution=8).intersects(test_area)
   geohash_cells = GeohashGrid(precision=6).intersects(test_area) 
   mgrs_cells = MGRSGrid(precision=2).intersects(test_area)

   print(f"H3 cells: {len(h3_cells)}")
   print(f"Geohash cells: {len(geohash_cells)}")
   print(f"MGRS cells: {len(mgrs_cells)}")

Working with Neighbors
----------------------

Find neighboring cells:

.. code-block:: python

   # Get a cell and its neighbors
   center_cell = h3_grid.get_cell_from_point(40.7128, -74.0060)
   neighbors = h3_grid.get_neighbors(center_cell)

   print(f"Center cell: {center_cell.identifier}")
   print(f"Number of neighbors: {len(neighbors)}")
   for neighbor in neighbors:
       print(f"  Neighbor: {neighbor.identifier}")

UTM Zone Information
--------------------

M3S automatically provides UTM zone information for accurate area calculations:

.. code-block:: python

   # The intersects() method includes UTM zone information
   result = h3_grid.intersects(gdf)
   
   # Group by UTM zone
   for utm_zone in result['utm'].unique():
       zone_data = result[result['utm'] == utm_zone]
       cities = zone_data['city'].unique()
       print(f"UTM Zone {utm_zone}: {', '.join(cities)}")

   # Reproject to UTM for accurate area calculations
   for utm_zone in result['utm'].unique():
       zone_cells = result[result['utm'] == utm_zone].copy()
       utm_crs = f"EPSG:{utm_zone}"
       zone_cells_utm = zone_cells.to_crs(utm_crs)
       zone_cells_utm['area_km2'] = zone_cells_utm.geometry.area / 1_000_000
       print(f"Zone {utm_zone} total area: {zone_cells_utm['area_km2'].sum():.2f} km²")

Error Handling
--------------

M3S provides clear error messages for common issues:

.. code-block:: python

   try:
       # Invalid precision values
       invalid_grid = H3Grid(resolution=20)  # Max is 15
   except ValueError as e:
       print(f"Error: {e}")

   try:
       # GeoDataFrame without CRS
       gdf_no_crs = gpd.GeoDataFrame(geometry=[Point(0, 0)])
       result = h3_grid.intersects(gdf_no_crs)
   except ValueError as e:
       print(f"Error: {e}")

Next Steps
----------

* Check out the :doc:`examples` for more detailed use cases
* Explore the :doc:`api` for complete method documentation
* See the example scripts in the repository for visualization examples