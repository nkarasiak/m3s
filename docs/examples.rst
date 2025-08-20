Examples
========

This page contains detailed examples showing how to use M3S for various spatial analysis tasks.

Grid Visualization Example
---------------------------

This example shows how to generate and visualize different grid types for the same area:

.. literalinclude:: ../examples/grid_generation_example.py
   :language: python
   :caption: Grid Generation and Visualization

The script creates three different grid systems (MGRS, H3, and Geohash) for a small area around Paris and visualizes them using matplotlib. Each grid system tessellates the space differently:

* **MGRS**: Square UTM-based grid cells
* **H3**: Hexagonal hierarchical grid cells  
* **Geohash**: Base32-encoded rectangular grid cells

UTM Reprojection Example
-------------------------

This example demonstrates how to use the UTM zone information provided by M3S for accurate area calculations:

.. literalinclude:: ../examples/utm_reprojection_example.py
   :language: python
   :caption: UTM Zone Detection and Area Calculation

The script shows how M3S automatically detects the optimal UTM zone for each grid cell, enabling accurate area calculations across different geographic regions.

Custom Analysis Examples
-------------------------

Point-in-Polygon Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import geopandas as gpd
   from shapely.geometry import Point, Polygon
   from m3s import H3Grid

   # Create a polygon (e.g., city boundary)
   city_boundary = Polygon([
       (-74.05, 40.70), (-73.95, 40.70),
       (-73.95, 40.80), (-74.05, 40.80), (-74.05, 40.70)
   ])
   
   city_gdf = gpd.GeoDataFrame(
       {'name': ['City']}, 
       geometry=[city_boundary], 
       crs="EPSG:4326"
   )

   # Generate H3 grid covering the city
   grid = H3Grid(resolution=9)  # ~650m cells
   city_cells = grid.intersects(city_gdf)
   
   print(f"City covered by {len(city_cells)} H3 cells")
   
   # Calculate total area in UTM projection
   utm_zone = city_cells['utm'].iloc[0]
   city_cells_utm = city_cells.to_crs(f"EPSG:{utm_zone}")
   total_area_km2 = city_cells_utm.geometry.area.sum() / 1_000_000
   print(f"Total area: {total_area_km2:.2f} km²")

Multi-Resolution Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from m3s import H3Grid
   
   # Analyze the same area at different resolutions
   point_gdf = gpd.GeoDataFrame(
       {'id': [1]}, 
       geometry=[Point(-74.0060, 40.7128)], 
       crs="EPSG:4326"
   )
   
   resolutions = [6, 7, 8, 9, 10]
   for res in resolutions:
       grid = H3Grid(resolution=res)
       cell = grid.intersects(point_gdf)
       
       # Get cell area
       utm_zone = cell['utm'].iloc[0]
       cell_utm = cell.to_crs(f"EPSG:{utm_zone}")
       area_km2 = cell_utm.geometry.area.iloc[0] / 1_000_000
       
       print(f"Resolution {res}: {area_km2:.6f} km² per cell")

Grid System Comparison
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   import matplotlib.pyplot as plt
   from m3s import H3Grid, GeohashGrid, MGRSGrid
   
   # Test area
   test_area = gpd.GeoDataFrame(
       {'name': ['Test']},
       geometry=[Point(-74.0060, 40.7128).buffer(0.01)],  # ~1km radius
       crs="EPSG:4326"
   )
   
   # Compare different grid systems
   grids = {
       'H3 (res 8)': H3Grid(resolution=8),
       'Geohash (p6)': GeohashGrid(precision=6), 
       'MGRS (p2)': MGRSGrid(precision=2)
   }
   
   fig, axes = plt.subplots(1, 3, figsize=(15, 5))
   
   for i, (name, grid) in enumerate(grids.items()):
       cells = grid.intersects(test_area)
       
       # Plot
       ax = axes[i]
       cells.plot(ax=ax, alpha=0.7, edgecolor='black')
       test_area.plot(ax=ax, color='red', alpha=0.3)
       ax.set_title(f'{name}\n{len(cells)} cells')
       ax.set_aspect('equal')
   
   plt.tight_layout()
   plt.show()

Performance Considerations
--------------------------

Working with Large Areas
~~~~~~~~~~~~~~~~~~~~~~~~~

For large areas, consider using appropriate grid resolutions:

.. code-block:: python

   # For country-level analysis
   country_grid = H3Grid(resolution=5)  # ~33km cells
   
   # For city-level analysis  
   city_grid = H3Grid(resolution=8)     # ~1.7km cells
   
   # For neighborhood-level analysis
   neighborhood_grid = H3Grid(resolution=10)  # ~240m cells

Batch Processing
~~~~~~~~~~~~~~~~

For processing many geometries efficiently:

.. code-block:: python

   # Process multiple areas at once
   areas_gdf = gpd.GeoDataFrame({
       'name': ['Area A', 'Area B', 'Area C'],
       'geometry': [polygon_a, polygon_b, polygon_c]
   }, crs="EPSG:4326")
   
   # Single call processes all geometries
   all_cells = grid.intersects(areas_gdf)
   
   # Results include original data for each intersecting cell
   for area_name in areas_gdf['name'].unique():
       area_cells = all_cells[all_cells['name'] == area_name]
       print(f"{area_name}: {len(area_cells)} cells")

Memory Management
~~~~~~~~~~~~~~~~~

For very fine resolutions over large areas:

.. code-block:: python

   # Process in chunks for memory efficiency
   def process_large_area(large_polygon, grid, chunk_size=0.1):
       bounds = large_polygon.bounds
       minx, miny, maxx, maxy = bounds
       
       all_cells = []
       y = miny
       while y < maxy:
           x = minx
           while x < maxx:
               # Create chunk
               chunk_poly = box(x, y, min(x + chunk_size, maxx), 
                              min(y + chunk_size, maxy))
               chunk_intersection = large_polygon.intersection(chunk_poly)
               
               if not chunk_intersection.is_empty:
                   chunk_gdf = gpd.GeoDataFrame(
                       {'chunk': [f'{x}_{y}']},
                       geometry=[chunk_intersection],
                       crs="EPSG:4326"
                   )
                   chunk_cells = grid.intersects(chunk_gdf)
                   all_cells.append(chunk_cells)
               
               x += chunk_size
           y += chunk_size
       
       return gpd.GeoDataFrame(pd.concat(all_cells, ignore_index=True))

More Examples
-------------

Check the ``examples/`` directory in the repository for additional examples:

* ``grid_generation_example.py`` - Complete visualization example
* ``utm_reprojection_example.py`` - UTM zone handling and area calculations

You can run these examples after installing M3S:

.. code-block:: bash

   python examples/grid_generation_example.py
   python examples/utm_reprojection_example.py