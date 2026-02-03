# M3S API Migration Guide

## Overview

M3S v0.5.1+ introduces a simplified API that makes spatial grid operations more intuitive while maintaining full backward compatibility with the existing API. This guide helps you understand both APIs and migrate when ready.

## Quick Summary

### New Simplified API (v0.5.1+)

**Best for**: Quick start, exploratory analysis, standard workflows

```python
import m3s

# Direct access, no instantiation
cell = m3s.Geohash.from_geometry((40.7, -74.0))
cells = m3s.H3.from_geometry(polygon)
neighbors = m3s.Geohash.neighbors(cell)
```

### Classic API (Still Supported)

**Best for**: Fine-grained control, advanced customization, existing codebases

```python
from m3s import GeohashGrid

grid = GeohashGrid(precision=5)
cell = grid.get_cell_from_point(40.7, -74.0)
```

## Complete API Comparison

### 1. Getting a Cell at a Point

**Classic API:**
```python
from m3s import GeohashGrid

grid = GeohashGrid(precision=5)
cell = grid.get_cell_from_point(40.7128, -74.0060)
print(cell.identifier)
```

**New API:**
```python
import m3s

# Option 1: Default precision
cell = m3s.Geohash.from_geometry((40.7128, -74.0060))

# Option 2: Explicit precision
cell = m3s.Geohash.with_precision(5).from_geometry((40.7128, -74.0060))

# Option 3: Precision parameter
cell = m3s.Geohash.from_geometry((40.7128, -74.0060), precision=5)

# Option 4: Explicit method
cell = m3s.Geohash.from_point(40.7128, -74.0060, precision=5)

print(cell.id)  # .id is alias for .identifier
```

### 2. Getting Cells in a Bounding Box

**Classic API:**
```python
from m3s import H3Grid

grid = H3Grid(resolution=7)
cells = grid.get_cells_in_bbox(
    min_lat=40.7, min_lon=-74.1,
    max_lat=40.8, max_lon=-73.9
)
```

**New API:**
```python
import m3s

# Option 1: Bbox tuple
cells = m3s.H3.from_geometry((40.7, -74.1, 40.8, -73.9))

# Option 2: Explicit method
cells = m3s.H3.from_bbox((40.7, -74.1, 40.8, -73.9))

# Option 3: With specific precision
cells = m3s.H3.with_precision(7).from_geometry((40.7, -74.1, 40.8, -73.9))
```

### 3. Getting Cells Intersecting a Polygon

**Classic API:**
```python
from m3s import MGRSGrid
import geopandas as gpd
from shapely.geometry import Polygon

polygon = Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)])
gdf = gpd.GeoDataFrame({'geometry': [polygon]}, crs='EPSG:4326')

grid = MGRSGrid(precision=3)
result_gdf = grid.intersects(gdf)
```

**New API:**
```python
import m3s
from shapely.geometry import Polygon

polygon = Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)])

# Works directly with Polygon (or GeoDataFrame)
cells = m3s.MGRS.from_geometry(polygon)

# Convert to GeoDataFrame
gdf = cells.to_gdf()
```

### 4. Finding Neighbors

**Classic API:**
```python
from m3s import GeohashGrid

grid = GeohashGrid(precision=5)
cell = grid.get_cell_from_point(40.7, -74.0)
neighbors = grid.get_neighbors(cell)
```

**New API:**
```python
import m3s

cell = m3s.Geohash.from_geometry((40.7, -74.0))
neighbors = m3s.Geohash.neighbors(cell, depth=1)

# Returns GridCellCollection
gdf = neighbors.to_gdf()
```

### 5. Getting Cell from Identifier

**Classic API:**
```python
from m3s import S2Grid

grid = S2Grid(level=10)
cell = grid.get_cell_from_identifier('89c25b')
```

**New API:**
```python
import m3s

# Automatically detects precision from identifier
cell = m3s.S2.from_id('89c25b')
```

### 6. Converting Between Grid Systems

**Classic API:**
```python
from m3s import GeohashGrid, convert_cell

geohash_grid = GeohashGrid(precision=5)
geohash_cell = geohash_grid.get_cell_from_point(40.7, -74.0)

# Convert to H3
h3_cell = convert_cell(geohash_cell, 'h3', method='centroid')
```

**New API:**
```python
import m3s

# Get cells in one system
cells = m3s.Geohash.from_geometry(polygon)

# Convert to another system
h3_cells = cells.to_h3()  # Uses centroid method by default
a5_cells = cells.to_a5(method='overlap')  # Or specify method
```

### 7. Working with Collections

**Classic API:**
```python
from m3s import H3Grid
import geopandas as gpd

grid = H3Grid(resolution=7)
gdf = grid.intersects(polygon_gdf)

# Manual filtering
large_cells = gdf[gdf['area_km2'] > 10.0]

# Get IDs
ids = gdf['cell_id'].tolist()
```

**New API:**
```python
import m3s

cells = m3s.H3.from_geometry(polygon)

# Built-in filtering
large_cells = cells.filter(lambda c: c.area_km2 > 10.0)

# Easy conversions
ids = cells.to_ids()
polygons = cells.to_polygons()
gdf = cells.to_gdf()

# Chaining
result = (cells
    .filter(lambda c: c.area_km2 > 10.0)
    .to_geohash()
    .to_gdf())
```

## New Features in Simplified API

### 1. Universal Geometry Handling

The new API accepts any geometry type:

```python
import m3s
from shapely.geometry import Point, Polygon
import geopandas as gpd

# Point tuple (lat, lon)
cell = m3s.H3.from_geometry((40.7, -74.0))

# Shapely Point
point = Point(-74.0, 40.7)
cell = m3s.H3.from_geometry(point)

# Shapely Polygon
polygon = Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)])
cells = m3s.H3.from_geometry(polygon)

# GeoDataFrame
gdf = gpd.GeoDataFrame({'geometry': [polygon]}, crs='EPSG:4326')
cells = m3s.H3.from_geometry(gdf)

# Bounding box tuple
cells = m3s.H3.from_geometry((40.7, -74.1, 40.8, -73.9))
```

### 2. Intelligent Precision Finding

**Not available in classic API**

```python
import m3s
from shapely.geometry import Polygon

polygon = Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)])

# By method
precision_auto = m3s.H3.find_precision(polygon, method='auto')  # Minimize variance
precision_less = m3s.H3.find_precision(polygon, method='less')  # Fewer cells
precision_more = m3s.H3.find_precision(polygon, method='more')  # More cells
precision_100 = m3s.H3.find_precision(polygon, method=100)      # Target ~100 cells

# By use case
precision = m3s.Geohash.find_precision_for_use_case('neighborhood')
# Available: 'building', 'block', 'neighborhood', 'city', 'region', 'country'

# By target area
precision = m3s.H3.find_precision_for_area(target_km2=10.0)
```

### 3. Collection Operations

**Not available in classic API**

```python
import m3s

cells = m3s.H3.from_geometry(polygon)

# Filter
large = cells.filter(lambda c: c.area_km2 > 10.0)

# Map
areas = cells.map(lambda c: c.area_km2)

# Properties
total_area = cells.total_area_km2
bounds = cells.bounds

# Export
ids = cells.to_ids()
polygons = cells.to_polygons()
gdf = cells.to_gdf()
dict_data = cells.to_dict()
```

### 4. GridCell Enhancements

New convenience properties and methods:

```python
import m3s

cell = m3s.Geohash.from_geometry((40.7, -74.0))

# New properties
cell.id            # Alias for .identifier
cell.centroid      # (lat, lon) tuple
cell.bounds        # (min_lon, min_lat, max_lon, max_lat)
cell.geometry      # Alias for .polygon

# New methods
cell.to_dict()     # Convert to dictionary
cell.to_geojson()  # Convert to GeoJSON feature
```

## Migration Strategies

### Strategy 1: Gradual Migration (Recommended)

Keep existing code unchanged, use new API for new features:

```python
# Existing code (still works)
from m3s import GeohashGrid
grid = GeohashGrid(precision=5)
cell = grid.get_cell_from_point(40.7, -74.0)

# New features with new API
import m3s
neighbors = m3s.Geohash.neighbors(cell)  # Works with old GridCell!
gdf = neighbors.to_gdf()
```

### Strategy 2: Module-by-Module

Migrate one module at a time:

```python
# Old module
def get_geohash_cells_old(lat, lon):
    from m3s import GeohashGrid
    grid = GeohashGrid(precision=5)
    return grid.get_cell_from_point(lat, lon)

# New module
def get_geohash_cells_new(lat, lon):
    import m3s
    return m3s.Geohash.from_geometry((lat, lon))
```

### Strategy 3: Wrapper Functions

Create wrappers for consistent interface:

```python
import m3s

def get_cell(system, lat, lon, precision=None):
    """Universal cell getter using new API"""
    grid = getattr(m3s, system.capitalize())
    if precision:
        return grid.with_precision(precision).from_geometry((lat, lon))
    return grid.from_geometry((lat, lon))

# Usage
cell = get_cell('geohash', 40.7, -74.0, precision=5)
cell = get_cell('h3', 40.7, -74.0)  # Uses default
```

## Performance Considerations

### Precision Finding Performance

**For large areas** (>10,000 estimated cells), the new API uses a fast path:

```python
import m3s

# Fast: uses default precision
cells = m3s.H3.from_geometry(very_large_polygon)

# Slower but optimal: finds best precision
precision = m3s.H3.find_precision(very_large_polygon, method='auto')
cells = m3s.H3.from_geometry(very_large_polygon, precision=precision)

# Recommended for large areas:
# 1. Find precision on a sample
sample = small_sample_of_area()
precision = m3s.H3.find_precision(sample, method='auto')

# 2. Use that precision for full area
cells = m3s.H3.from_geometry(full_area, precision=precision)
```

### Grid Instance Caching

The new API caches grid instances by precision:

```python
import m3s

# These reuse the same cached grid instance
cell1 = m3s.Geohash.from_geometry((40.7, -74.0))
cell2 = m3s.Geohash.from_geometry((40.8, -74.1))
neighbors = m3s.Geohash.neighbors(cell1)

# More efficient than repeatedly instantiating
from m3s import GeohashGrid
grid1 = GeohashGrid(precision=5)  # New instance
grid2 = GeohashGrid(precision=5)  # Another new instance
```

## Common Patterns

### Pattern 1: Exploratory Analysis

```python
import m3s
from shapely.geometry import Polygon

# Quick exploration with defaults
area = Polygon([...])
cells = m3s.H3.from_geometry(area)
print(f"Default: {len(cells)} cells")

# Try different precisions
for method in ['less', 'auto', 'more']:
    p = m3s.H3.find_precision(area, method=method)
    cells = m3s.H3.from_geometry(area, precision=p)
    print(f"{method}: precision={p}, cells={len(cells)}")
```

### Pattern 2: Production Pipeline

```python
import m3s

# Determine precision once
PRECISION = m3s.H3.find_precision_for_use_case('neighborhood')

def process_area(polygon):
    """Process area with consistent precision"""
    cells = m3s.H3.from_geometry(polygon, precision=PRECISION)
    return cells.to_gdf()
```

### Pattern 3: Multi-System Comparison

```python
import m3s

def compare_grids(geometry, systems=['Geohash', 'H3', 'A5']):
    """Compare different grid systems"""
    results = {}
    for system_name in systems:
        grid = getattr(m3s, system_name)
        cells = grid.from_geometry(geometry)
        results[system_name] = {
            'count': len(cells),
            'total_area': cells.total_area_km2,
            'cells': cells
        }
    return results

# Usage
results = compare_grids(polygon)
for system, data in results.items():
    print(f"{system}: {data['count']} cells, {data['total_area']:.2f} km²")
```

## Backward Compatibility Guarantee

**All existing code continues to work.** The new API is additive:

```python
# ✅ This still works (and always will)
from m3s import GeohashGrid, H3Grid, convert_cell
grid = GeohashGrid(precision=5)
cell = grid.get_cell_from_point(40.7, -74.0)

# ✅ New API is available alongside
import m3s
new_cell = m3s.Geohash.from_geometry((40.7, -74.0))

# ✅ They work together
neighbors = m3s.Geohash.neighbors(cell)  # Works with old cell!
```

## Getting Help

- **Documentation**: See [Quick Start Guide](quickstart_guide.md)
- **Examples**: Check [examples/quickstart_new_api.py](../examples/quickstart_new_api.py)
- **Issues**: Report problems at GitHub Issues
- **Questions**: Ask in GitHub Discussions

## Summary

| Aspect | Classic API | New Simplified API |
|--------|-------------|-------------------|
| **Setup** | Import grid class, instantiate | Import m3s, use directly |
| **Complexity** | More code, explicit steps | Less code, implicit defaults |
| **Flexibility** | Full control | Sensible defaults + control when needed |
| **Learning Curve** | Steeper | Gentler |
| **Use Case** | Advanced users, existing codebases | New users, quick start, exploration |
| **Performance** | Slightly faster (no auto-precision) | Optimized with caching |
| **Features** | Core functionality | Core + precision finding + collections |

**Recommendation**: Start with the simplified API, use classic API when you need fine-grained control.

Both APIs are fully supported and will remain so for the foreseeable future!
