"""
M3S Quick Start - New Simplified API
=====================================

This example demonstrates the new simplified API for quick start.

The new API provides:
- Direct access to grid systems via m3s.A5, m3s.Geohash, etc.
- Universal from_geometry() method handling any geometry type
- Auto-precision selection for optimal coverage
- Easy conversions between grid systems
- Convenient collection operations

.. note::
    All existing APIs remain functional for backward compatibility.
"""

import m3s
from shapely.geometry import Point, Polygon
import geopandas as gpd

# %%
# Example 1: Universal from_geometry() - works with any geometry type
# ---------------------------------------------------------------------
# The from_geometry() method accepts point tuples, Polygons, GeoDataFrames,
# and bounding box tuples. Precision is auto-selected for optimal coverage.

# Point tuple (lat, lon)
cell = m3s.Geohash.from_geometry((40.7128, -74.0060))
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
cells = m3s.A5.from_geometry(gdf)
print(f"\nA5 cells from GeoDataFrame: {len(cells)} cells")

# %%
# Example 4: Find optimal precision for your data
# ------------------------------------------------
# For best results with large areas, find precision explicitly first

# Target ~100 cells
precision = m3s.A5.find_precision(polygon, method=100)
cells = m3s.A5.from_geometry(polygon, precision=precision)
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
    (40.7, -74.1, 40.8, -73.9)  # Bbox tuple
)
result_gdf = cells.to_gdf()
print(f"\nCreated GeoDataFrame with {len(result_gdf)} MGRS cells")

# %%
# Example 6: Get neighbors
# ------------------------

cell = m3s.S2.from_geometry((40.7128, -74.0060))  # Point tuple
neighbors = m3s.S2.neighbors(cell, depth=1)
print(f"\nCell has {len(neighbors)} neighbors (including itself)")

# %%
# Example 7: Convert between grid systems
# ----------------------------------------
# Default conversion uses centroid method (fast, good for most cases)

geohash_cells = m3s.Geohash.from_geometry((40.7, -74.0))
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
    (40.7, -74.1, 40.8, -73.9)  # Bbox
)
print(f"\nNeighborhood-level precision {precision}: {len(cells)} cells")

# Other use cases: 'building', 'block', 'city', 'region', 'country'
building_precision = m3s.Geohash.find_precision_for_use_case("building")
city_precision = m3s.A5.find_precision_for_use_case("city")
print(f"Building precision: {building_precision}")
print(f"City precision: {city_precision}")

# %%
# Example 10: Specific geometry methods when clarity is preferred
# ----------------------------------------------------------------

cell = m3s.MGRS.from_point(40.7128, -74.0060)  # Explicit point method
cells = m3s.S2.from_bbox((40.7, -74.1, 40.8, -73.9))  # Explicit bbox method
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
# Example 12: Hierarchical operations
# ------------------------------------

# Get children at higher precision
cell = m3s.Geohash.from_geometry((40.7, -74.0))
neighbors = m3s.Geohash.neighbors(cell)

# This requires parent/child methods - only works for grids that support it
# children = neighbors.refine(precision=7)
# print(f"Refined to {len(children)} children cells")

# %%
# Example 13: Comparison with old API
# ------------------------------------

print("\n" + "=" * 60)
print("Comparison: Old API vs New API")
print("=" * 60)

# Old API (still works!)
print("\nOld API:")
from m3s import GeohashGrid

grid = GeohashGrid(precision=5)
old_cell = grid.get_cell_from_point(40.7, -74.0)
print(f"Cell: {old_cell.identifier}")

# New API (much simpler!)
print("\nNew API:")
new_cell = m3s.Geohash.from_geometry((40.7, -74.0))
print(f"Cell: {new_cell.id}")

print("\nBoth APIs work! New API is simpler for quick start.")

# %%
# Example 14: Advanced workflow with chaining
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
# 1. Direct access: m3s.A5, m3s.Geohash, etc. (no instantiation needed)
# 2. Universal from_geometry(): handles any geometry type
# 3. Auto-precision: intelligent defaults based on coverage optimization
# 4. Easy conversions: .to_h3(), .to_geohash(), etc.
# 5. Convenient operations: .filter(), .to_gdf(), .to_ids(), etc.
# 6. Full backward compatibility: old API still works

print("\n" + "=" * 60)
print("New API makes M3S easier to use while maintaining full power!")
print("=" * 60)
