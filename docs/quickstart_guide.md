# M3S Quick Start Guide

## Introduction

M3S provides two APIs for working with spatial grid systems:

1. **New Simplified API (Recommended)**: Direct access to grids with auto-precision and universal geometry handling
2. **Classic API**: Traditional grid instantiation for advanced control

This guide focuses on the new simplified API introduced in v0.5.1.

## Core Concepts

### Grid Systems

M3S supports 12 different spatial grid systems, each accessible via a singleton instance:

```python
import m3s

# Access any grid system directly
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
```

### GridCell

A `GridCell` represents a single grid cell with:

- `.id` or `.identifier`: Unique cell identifier
- `.precision`: Precision/resolution level
- `.area_km2`: Cell area in square kilometers
- `.polygon` or `.geometry`: Shapely polygon
- `.bounds`: Bounding box (min_lon, min_lat, max_lon, max_lat)
- `.centroid`: Center point (lat, lon)

### GridCellCollection

A `GridCellCollection` is a container for multiple cells with utility methods:

- `.to_gdf()`: Convert to GeoDataFrame
- `.to_ids()`: Get list of cell IDs
- `.to_polygons()`: Get list of polygons
- `.filter()`: Filter cells by predicate
- `.map()`: Apply function to each cell
- `.to_h3()`, `.to_geohash()`, etc.: Convert to other grid systems

## Basic Usage

### Working with Points

```python
import m3s

# Point as tuple (lat, lon)
cell = m3s.Geohash.from_geometry((40.7128, -74.0060))
print(f"Cell: {cell.id}")
print(f"Area: {cell.area_km2:.2f} km²")
print(f"Centroid: {cell.centroid}")

# Shapely Point
from shapely.geometry import Point
point = Point(-74.0060, 40.7128)
cell = m3s.H3.from_geometry(point)

# Explicit method (for clarity)
cell = m3s.MGRS.from_point(40.7128, -74.0060)
```

### Working with Areas

```python
import m3s
from shapely.geometry import Polygon

# Polygon
polygon = Polygon([
    (-74.1, 40.7), (-73.9, 40.7),
    (-73.9, 40.8), (-74.1, 40.8)
])
cells = m3s.H3.from_geometry(polygon)  # Auto-precision
print(f"Found {len(cells)} cells")
print(f"Total area: {cells.total_area_km2:.2f} km²")

# Bounding box as tuple (min_lat, min_lon, max_lat, max_lon)
cells = m3s.Geohash.from_geometry((40.7, -74.1, 40.8, -73.9))

# GeoDataFrame
import geopandas as gpd
gdf = gpd.GeoDataFrame({'geometry': [polygon]}, crs='EPSG:4326')
cells = m3s.A5.from_geometry(gdf)

# Explicit methods
cells = m3s.S2.from_bbox((40.7, -74.1, 40.8, -73.9))
cells = m3s.Quadkey.from_polygon(polygon)
```

## Precision Selection

### Auto-Precision

By default, `from_geometry()` automatically selects precision to minimize coverage variance:

```python
polygon = Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)])

# Auto-precision (minimizes coverage variance)
cells = m3s.H3.from_geometry(polygon)
```

### Explicit Precision

Specify precision when you need control:

```python
# Method 1: with_precision()
cells = m3s.Geohash.with_precision(7).from_geometry(polygon)

# Method 2: precision parameter
cells = m3s.H3.from_geometry(polygon, precision=9)
cell = m3s.A5.from_point(40.7, -74.0, precision=10)
```

### Finding Optimal Precision

#### By Method

```python
# Auto: minimize coverage variance (default)
precision = m3s.H3.find_precision(polygon, method='auto')

# Less: prefer fewer, larger cells (10-50 cells)
precision = m3s.Geohash.find_precision(polygon, method='less')

# More: prefer more, smaller cells (200-1000 cells)
precision = m3s.A5.find_precision(polygon, method='more')

# Balanced: balance coverage quality and cell count
precision = m3s.S2.find_precision(polygon, method='balanced')

# Target count: aim for specific number of cells
precision = m3s.H3.find_precision(polygon, method=100)  # Target ~100 cells
```

#### By Target Area

```python
# Find precision where cells are ~10 km²
precision = m3s.Geohash.find_precision_for_area(target_km2=10.0)

# With tolerance
precision = m3s.H3.find_precision_for_area(target_km2=5.0, tolerance=0.1)
```

#### By Use Case

```python
# Predefined use cases
precision = m3s.A5.find_precision_for_use_case('building')      # ~0.001-0.01 km²
precision = m3s.Geohash.find_precision_for_use_case('block')    # ~0.01-0.1 km²
precision = m3s.H3.find_precision_for_use_case('neighborhood')  # ~1-10 km²
precision = m3s.MGRS.find_precision_for_use_case('city')        # ~100-1000 km²
precision = m3s.S2.find_precision_for_use_case('region')        # ~10,000-100,000 km²
precision = m3s.Quadkey.find_precision_for_use_case('country')  # ~100,000+ km²
```

## Neighbors

Get neighboring cells:

```python
# Get cell
cell = m3s.Geohash.from_geometry((40.7, -74.0))

# Get neighbors (depth=1 includes cell + immediate neighbors)
neighbors = m3s.Geohash.neighbors(cell, depth=1)
print(f"Found {len(neighbors)} cells (including original)")

# Depth=2 includes neighbors of neighbors
expanded = m3s.H3.neighbors(cell, depth=2)
```

## Collection Operations

### Conversion

```python
cells = m3s.H3.from_geometry(polygon)

# Convert to GeoDataFrame
gdf = cells.to_gdf()
gdf_with_utm = cells.to_gdf(include_utm=True)

# Convert to lists
ids = cells.to_ids()           # List[str]
polygons = cells.to_polygons() # List[Polygon]

# Convert to dict
data = cells.to_dict()
```

### Filtering

```python
# Filter by area
large_cells = cells.filter(lambda c: c.area_km2 > 10.0)

# Filter by custom predicate
def is_in_nyc(cell):
    lat, lon = cell.centroid
    return 40.5 <= lat <= 40.9 and -74.3 <= lon <= -73.7

nyc_cells = cells.filter(is_in_nyc)
```

### Mapping

```python
# Extract areas
areas = cells.map(lambda c: c.area_km2)

# Extract centroids
centroids = cells.map(lambda c: c.centroid)
```

### Properties

```python
# Total area
total = cells.total_area_km2

# Bounds
min_lon, min_lat, max_lon, max_lat = cells.bounds

# Length
count = len(cells)

# Iteration
for cell in cells:
    print(cell.id)

# Indexing
first_cell = cells[0]
subset = cells[0:10]  # Returns GridCellCollection
```

## Cross-Grid Conversion

Convert between grid systems:

```python
# Get cells in one system
geohash_cells = m3s.Geohash.from_geometry(polygon)

# Convert to another system (centroid method by default)
h3_cells = geohash_cells.to_h3()
a5_cells = geohash_cells.to_a5()
s2_cells = geohash_cells.to_s2()

# Specify conversion method
h3_cells_overlap = geohash_cells.to_h3(method='overlap')      # More accurate
h3_cells_containment = geohash_cells.to_h3(method='containment')  # Contains centroid

# All conversion methods
cells.to_h3()
cells.to_geohash()
cells.to_a5()
cells.to_mgrs()
cells.to_s2()
cells.to_quadkey()
cells.to_slippy()
cells.to_csquares()
cells.to_gars()
cells.to_maidenhead()
cells.to_pluscode()
cells.to_what3words()
```

## Advanced Workflows

### Chaining Operations

```python
# Complex workflow with method chaining
result = (
    m3s.H3.from_geometry(polygon, precision=7)
    .filter(lambda c: c.area_km2 > 5.0)
    .to_geohash()
    .to_gdf()
)
```

### Working with Multiple Geometries

```python
import geopandas as gpd
from shapely.geometry import Polygon

# Create GeoDataFrame with multiple areas
geometries = [
    Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)]),
    Polygon([(-118.5, 34.0), (-118.3, 34.0), (-118.3, 34.2), (-118.5, 34.2)])
]
gdf = gpd.GeoDataFrame({'geometry': geometries}, crs='EPSG:4326')

# Get cells for all geometries
cells = m3s.H3.from_geometry(gdf)

# Find precision optimal for all geometries
precision = m3s.H3.find_precision(gdf, method='auto')
```

### Hierarchical Operations

```python
# Get parent cells (coarser precision)
cells = m3s.Geohash.from_geometry(polygon, precision=7)
parents = cells.coarsen(precision=5)

# Get child cells (finer precision)
children = cells.refine(precision=9)
```

## GridCell Enhancements

```python
cell = m3s.Geohash.from_geometry((40.7, -74.0))

# Convenience properties
cell.id              # Alias for identifier
cell.bounds          # (min_lon, min_lat, max_lon, max_lat)
cell.centroid        # (lat, lon)
cell.geometry        # Alias for polygon

# Conversion methods
cell_dict = cell.to_dict()
geojson = cell.to_geojson()
```

## Migration from Classic API

### Before (Classic API)

```python
from m3s import GeohashGrid

# Must instantiate with precision
grid = GeohashGrid(precision=5)
cell = grid.get_cell_from_point(40.7, -74.0)

# Verbose method names
cells = grid.get_cells_in_bbox(40.7, -74.1, 40.8, -73.9)
neighbors = grid.get_neighbors(cell)
```

### After (New Simplified API)

```python
import m3s

# Direct access, auto-precision
cell = m3s.Geohash.from_geometry((40.7, -74.0))

# Universal method, shorter names
cells = m3s.Geohash.from_geometry((40.7, -74.1, 40.8, -73.9))
neighbors = m3s.Geohash.neighbors(cell)
```

**Note:** The classic API still works! Use whichever style fits your needs.

## Best Practices

### 1. Use Auto-Precision for Exploratory Analysis

```python
# Let M3S pick optimal precision
cells = m3s.H3.from_geometry(area_of_interest)
```

### 2. Use Specific Precision for Production

```python
# Lock in precision for consistency
precision = m3s.H3.find_precision(sample_area, method='auto')
cells = m3s.H3.from_geometry(production_areas, precision=precision)
```

### 3. Use Use-Case Precision for Common Scenarios

```python
# Quick precision for typical use cases
precision = m3s.Geohash.find_precision_for_use_case('neighborhood')
cells = m3s.Geohash.from_geometry(area, precision=precision)
```

### 4. Choose Conversion Method Wisely

```python
# Fast: centroid method (default)
h3_cells = geohash_cells.to_h3()  # Good for most cases

# Accurate: overlap method
h3_cells = geohash_cells.to_h3(method='overlap')  # Better coverage

# Strict: containment method
h3_cells = geohash_cells.to_h3(method='containment')  # Only cells containing centroid
```

### 5. Use Collections for Batch Operations

```python
# Efficient: work with collections
cells = m3s.H3.from_geometry(large_area)
large_cells = cells.filter(lambda c: c.area_km2 > 10)
gdf = large_cells.to_gdf()

# Avoid: individual cell operations
# for cell in cells:  # Less efficient
#     if cell.area_km2 > 10:
#         ...
```

## Common Patterns

### Pattern 1: Find Cells in Area of Interest

```python
aoi = get_area_of_interest()  # Your area
cells = m3s.H3.from_geometry(aoi)
gdf = cells.to_gdf()
```

### Pattern 2: Grid Comparison

```python
area = Polygon([...])

# Compare different grid systems
geohash_cells = m3s.Geohash.from_geometry(area)
h3_cells = m3s.H3.from_geometry(area)
a5_cells = m3s.A5.from_geometry(area)

print(f"Geohash: {len(geohash_cells)} cells")
print(f"H3: {len(h3_cells)} cells")
print(f"A5: {len(a5_cells)} cells")
```

### Pattern 3: Spatial Join with Grid Cells

```python
# Create grid
cells = m3s.H3.from_geometry(study_area)
grid_gdf = cells.to_gdf()

# Spatial join with your data
import geopandas as gpd
data_gdf = gpd.read_file('data.geojson')
joined = gpd.sjoin(data_gdf, grid_gdf, how='left', predicate='intersects')
```

### Pattern 4: Multi-Resolution Analysis

```python
# Coarse overview
coarse_cells = m3s.H3.with_precision(5).from_geometry(large_area)

# Fine detail for specific regions
for cell in coarse_cells:
    if is_interesting(cell):
        fine_cells = m3s.H3.with_precision(10).from_geometry(cell.polygon)
        analyze(fine_cells)
```

## Troubleshooting

### Issue: Too Many Cells

```python
# Problem: Auto-precision creates too many cells
cells = m3s.H3.from_geometry(very_large_area)  # Could be millions!

# Solution 1: Use 'less' method
precision = m3s.H3.find_precision(very_large_area, method='less')
cells = m3s.H3.from_geometry(very_large_area, precision=precision)

# Solution 2: Target specific count
precision = m3s.H3.find_precision(very_large_area, method=1000)  # Max 1000 cells
cells = m3s.H3.from_geometry(very_large_area, precision=precision)

# Solution 3: Use coarser default precision
cells = m3s.H3.with_precision(3).from_geometry(very_large_area)
```

### Issue: Too Few Cells

```python
# Problem: Need finer granularity
cells = m3s.Geohash.from_geometry(small_area)  # Only a few cells

# Solution: Use 'more' method or higher precision
precision = m3s.Geohash.find_precision(small_area, method='more')
cells = m3s.Geohash.from_geometry(small_area, precision=precision)
```

### Issue: Precision Unclear

```python
# Problem: Don't know what precision to use

# Solution 1: Use use-case precision
precision = m3s.H3.find_precision_for_use_case('neighborhood')

# Solution 2: Use target area
precision = m3s.H3.find_precision_for_area(target_km2=10.0)

# Solution 3: Experiment with sample
sample = small_sample_of_area()
for method in ['less', 'auto', 'more']:
    p = m3s.H3.find_precision(sample, method=method)
    cells = m3s.H3.from_geometry(sample, precision=p)
    print(f"{method}: precision={p}, cells={len(cells)}")
```

## Summary

The new M3S simplified API provides:

✅ **Easy access**: `m3s.A5`, `m3s.Geohash`, etc.
✅ **Universal methods**: `from_geometry()` handles any geometry type
✅ **Auto-precision**: Intelligent defaults based on coverage optimization
✅ **Easy conversion**: `.to_h3()`, `.to_geohash()`, etc.
✅ **Convenient operations**: `.filter()`, `.to_gdf()`, `.to_ids()`, etc.
✅ **Full backward compatibility**: Classic API still works

Start simple with auto-precision, refine as needed, and leverage collections for powerful spatial analysis!
