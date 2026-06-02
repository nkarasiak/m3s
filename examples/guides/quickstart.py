"""
Quickstart
==========

The simplified, GIS-native M3S API — the recommended entry point.

It provides:

- Direct access to grid systems via ``m3s.H3``, ``m3s.Geohash``, etc.
- A universal ``from_geometry()`` method handling any geometry type
- Auto-precision selection for optimal coverage
- Easy conversions between grid systems
- Convenient collection operations

All coordinate tuples use GIS-native ``(lon, lat)`` order.
"""

import geopandas as gpd
from shapely.geometry import Polygon

import m3s

# %%
# Example 1: Universal from_geometry() - works with any geometry type
# ---------------------------------------------------------------------
# The from_geometry() method accepts point tuples, Polygons, GeoDataFrames,
# and bounding box tuples. Precision is auto-selected for optimal coverage.

# Point tuple (lon, lat) - GIS-native axis order
cell = m3s.Geohash.from_geometry((-74.0060, 40.7128))
print(f"Cell: {cell.id}, Area: {cell.area_km2:.2f} km²")
print(f"Centroid: {cell.centroid}")
print(f"Bounds: {cell.bounds}")

# %%
# Example 2: from_geometry() with Polygon
# -----------------------------------------
# Uses default precision (or specify for optimal coverage)

polygon = Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)])
cells = m3s.H3.from_geometry(polygon)  # Uses default precision (7)
print(f"\nFound {len(cells)} H3 cells")
print(f"Total area: {cells.total_area_km2:.2f} km²")

# %%
# Example 3: from_geometry() with GeoDataFrame
# ---------------------------------------------

gdf = gpd.GeoDataFrame({"geometry": [polygon]}, crs="EPSG:4326")
cells = m3s.S2.from_geometry(gdf)
print(f"\nS2 cells from GeoDataFrame: {len(cells)} cells")

# %%
# Example 4: Find optimal precision for your data
# ------------------------------------------------
# For best results with large areas, find precision explicitly first

# Target ~100 cells
precision = m3s.S2.find_precision(polygon, method=100)
cells = m3s.S2.from_geometry(polygon, precision=precision)
print(f"\nUsing precision {precision}: {len(cells)} cells")

# Minimize coverage variance ('auto' method - recommended for quality)
precision_auto = m3s.H3.find_precision(polygon, method="auto")
cells_auto = m3s.H3.from_geometry(polygon, precision=precision_auto)
print(f"Auto precision (minimize variance): {precision_auto}, {len(cells_auto)} cells")

# Fewer, larger cells
precision_less = m3s.H3.find_precision(polygon, method="less")
print(f"Fewer cells precision: {precision_less}")

# More, smaller cells
precision_more = m3s.H3.find_precision(polygon, method="more")
print(f"More cells precision: {precision_more}")

# %%
# Example 5: Work with specific precision using with_precision()
# ---------------------------------------------------------------

cells = m3s.MGRS.with_precision(5).from_geometry(
    (-74.1, 40.7, -73.9, 40.8)  # Bbox tuple (min_lon, min_lat, max_lon, max_lat)
)
result_gdf = cells.to_gdf()
print(f"\nCreated GeoDataFrame with {len(result_gdf)} MGRS cells")

# %%
# Example 6: Get neighbors
# ------------------------

cell = m3s.S2.from_geometry((-74.0060, 40.7128))  # Point tuple (lon, lat)
neighbors = m3s.S2.neighbors(cell, depth=1)
print(f"\nCell has {len(neighbors)} neighbors (including itself)")

# %%
# Example 7: Convert between grid systems
# ----------------------------------------
# Default conversion uses centroid method (fast, good for most cases)

geohash_cells = m3s.Geohash.from_geometry((-74.0, 40.7))
neighbors_with_origin = m3s.Geohash.neighbors(geohash_cells)
h3_cells = neighbors_with_origin.to_h3()  # Centroid method (default)
print(f"\nConverted {len(neighbors_with_origin)} Geohash → {len(h3_cells)} H3")

# %%
# Example 8: Explicit conversion method if needed
# ------------------------------------------------

h3_cells_overlap = neighbors_with_origin.to_h3(method="overlap")  # More accurate
print(f"With overlap method: {len(h3_cells_overlap)} H3 cells")

# %%
# Example 9: Precision for use cases
# -----------------------------------

precision = m3s.H3.find_precision_for_use_case("neighborhood")
cells = m3s.H3.with_precision(precision).from_geometry(
    (-74.1, 40.7, -73.9, 40.8)  # Bbox (min_lon, min_lat, max_lon, max_lat)
)
print(f"\nNeighborhood-level precision {precision}: {len(cells)} cells")

# Other use cases: 'building', 'block', 'city', 'region', 'country'
building_precision = m3s.Geohash.find_precision_for_use_case("building")
city_precision = m3s.S2.find_precision_for_use_case("city")
print(f"Building precision: {building_precision}")
print(f"City precision: {city_precision}")

# %%
# Example 10: Specific geometry methods when clarity is preferred
# ----------------------------------------------------------------

cell = m3s.MGRS.from_point(-74.0060, 40.7128)  # Explicit point method (lon, lat)
cells = m3s.S2.from_bbox((-74.1, 40.7, -73.9, 40.8))  # Explicit bbox method
cells = m3s.Quadkey.from_polygon(polygon)  # Explicit polygon method

print(f"\nUsed specific methods: {len(cells)} Quadkey cells")

# %%
# Example 11: Collection operations
# ----------------------------------
# GridCellCollection provides convenient operations

cells = m3s.H3.from_geometry(polygon, precision=7)

# Filter cells by area
large_cells = cells.filter(lambda c: c.area_km2 > 5.0)
print(f"\nFiltered to {len(large_cells)} cells > 5 km²")

# Convert to different formats
ids_list = cells.to_ids()
polygons_list = cells.to_polygons()
gdf = cells.to_gdf(include_utm=True)
print(f"Converted to {len(ids_list)} IDs, {len(polygons_list)} polygons")

# %%
# Example 12: Advanced workflow with chaining
# --------------------------------------------

# Complex workflow: geometry → cells → neighbors → convert → export
result = (
    m3s.H3.from_geometry(polygon, precision=7)
    .filter(lambda c: c.area_km2 > 3.0)
    .to_geohash()
)
print(f"\nChained workflow result: {len(result)} cells")

# %%
# Summary
# -------
# The new API provides:
# 1. Direct access: m3s.H3, m3s.Geohash, m3s.S2, etc. (no instantiation needed)
# 2. Universal from_geometry(): handles any geometry type
# 3. Auto-precision: intelligent defaults based on coverage optimization
# 4. Easy conversions: .to_h3(), .to_geohash(), etc.
# 5. Convenient operations: .filter(), .to_gdf(), .to_ids(), etc.

print("\n" + "=" * 60)
print("The simplified API makes M3S easy to use without sacrificing power!")
print("=" * 60)
