# M3S - Multi Spatial Subdivision System

A unified Python package for working with hierarchical spatial grid systems. M3S (Multi Spatial Subdivision System) provides a consistent interface for working with different spatial indexing systems including Geohash, MGRS, H3, Quadkey, S2, Slippy Map tiles, C-squares, GARS, Maidenhead, Plus Codes, and What3Words.

## Features

### ✨ New Simplified API (v0.5.1+)
- **🎯 Direct Grid Access**: No instantiation needed—just `m3s.H3`, `m3s.Geohash`, etc.
- **🌐 Universal Geometry**: Single `from_geometry()` handles points, polygons, bboxes, GeoDataFrames
- **🔍 Smart Precision**: Auto-select optimal precision or choose by use case, area, or cell count
- **🔄 Easy Conversion**: Convert between grids with `.to_h3()`, `.to_geohash()`, etc.
- **📦 Powerful Collections**: Filter, map, export with `GridCellCollection`
- **🔙 Fully Compatible**: Existing code works unchanged

### Core Capabilities
- **11 Grid Systems**: Geohash, MGRS, H3, Quadkey, S2, Slippy, C-squares, GARS, Maidenhead, Plus Codes, What3Words
- **Area Calculations**: All grids support `area_km2` property
- **GeoPandas Integration**: Native GeoDataFrame support with automatic CRS transformation
- **UTM Zone Integration**: Automatic UTM zone detection and inclusion
- **Polygon Intersection**: Find grid cells intersecting any Shapely polygon or GeoDataFrame
- **Hierarchical Operations**: Parent/child relationships and multi-resolution analysis
- **Neighbor Finding**: Get neighboring cells across all grid systems
- **Parallel Processing**: Threaded parallelism and streaming for large datasets
- **Modern Python**: Type hints, comprehensive documentation and test suite

## Installation

```bash
uv pip install m3s
```

For development:

```bash
git clone https://github.com/nkarasiak/m3s.git
cd m3s
uv pip install -e ".[dev]"
```

## Quick Start

### ✨ New Simplified API (v0.5.1+)

The new simplified API makes M3S easier to use with direct access to grid systems, auto-precision selection, and universal geometry handling:

```python
import m3s
from shapely.geometry import Polygon

# Direct access to grid systems (no instantiation needed!)
# Coordinate tuples use GIS-native (lon, lat) / (x, y) order, like shapely.
cell = m3s.Geohash.from_geometry((-74.0060, 40.7128))  # Point tuple (lon, lat)
print(f"Cell: {cell.id}, Area: {cell.area_km2:.2f} km²")
# Output: Cell: dr5re, Area: 18.11 km²

# Works with any geometry type: points, polygons, GeoDataFrames, bbox tuples
polygon = Polygon([(-74.1, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.1, 40.8)])
cells = m3s.H3.from_geometry(polygon)  # Uses default precision (7)
print(f"Found {len(cells)} H3 cells with total area {cells.total_area_km2:.2f} km²")
# Output: Found 47 H3 cells with total area 244.01 km²

# For optimal precision with large areas, find it explicitly first:
precision = m3s.H3.find_precision(polygon, method='auto')  # Minimizes coverage variance
cells = m3s.H3.from_geometry(polygon, precision=precision)

# Get neighbors
neighbors = m3s.Geohash.neighbors(cell, depth=1)
print(f"Cell has {len(neighbors)} neighbors (including itself)")
# Output: Cell has 9 neighbors (including itself)

# Or find optimal precision
precision = m3s.H3.find_precision(polygon, method='auto')  # Minimizes coverage variance
cells = m3s.H3.from_geometry(polygon, precision=precision)

# Easy conversions between grid systems
h3_cells = cells.to_geohash()  # Convert H3 → Geohash
gdf = h3_cells.to_gdf()        # Convert to GeoDataFrame

# Collection operations
large_cells = cells.filter(lambda c: c.area_km2 > 10.0)
ids = cells.to_ids()
polygons = cells.to_polygons()

# Find precision by use case
precision = m3s.Geohash.find_precision_for_use_case('neighborhood')  # ~1-10 km²
# Other use cases: 'building', 'block', 'city', 'region', 'country'
```

**Available grid systems:**
- `m3s.Geohash` - Base32-encoded spatial index
- `m3s.MGRS` - Military Grid Reference System
- `m3s.H3` - Uber's hexagonal grid
- `m3s.S2` - Google's spherical geometry
- `m3s.Quadkey` - Microsoft Bing Maps tiles
- `m3s.Slippy` - OpenStreetMap tiles
- `m3s.CSquares` - Marine data indexing
- `m3s.GARS` - Global Area Reference System
- `m3s.Maidenhead` - Amateur radio locator
- `m3s.PlusCode` - Open Location Codes
- `m3s.What3Words` - 3-meter precision squares

> **Coordinate order:** the simplified API uses GIS-native **(lon, lat)** / (x, y)
> order for coordinate tuples — matching shapely, geopandas and pyproj.
> `GridCell.bounds`, `GridCell.centroid` and `from_bbox` all follow the same
> order, so `grid.from_bbox(collection.bounds)` round-trips correctly. The
> classic low-level `Grid.get_cell_from_point(lat, lon)` keeps explicit
> `lat, lon` parameters.

### 🆚 API Comparison

| Task | New Simplified API | Classic API |
|------|-------------------|-------------|
| **Get cell at point** | `m3s.Geohash.from_geometry((-74.0, 40.7))` | `GeohashGrid(precision=5).get_cell_from_point(40.7, -74.0)` |
| **Get cells in area** | `m3s.H3.from_geometry(polygon)` | `H3Grid(resolution=7).intersects(gdf)` |
| **Get neighbors** | `m3s.Geohash.neighbors(cell)` | `grid.get_neighbors(cell)` |
| **Find precision** | `m3s.H3.find_precision_for_use_case('city')` | Manual selection |
| **Convert grids** | `cells.to_h3()` | Use conversion utilities |
| **Export** | `cells.to_gdf()` | Multiple steps |

### Which API should I use?

M3S has one recommended path and two optional tiers. **If unsure, use the
Simplified API** — it covers the large majority of use cases.

1. **Simplified API (recommended, the golden path)** — `m3s.H3`, `m3s.Geohash`, …
   Direct access, `from_geometry()`, `find_precision*()`, `GridCellCollection`
   (`.filter()`, `.to_gdf()`, `.to_h3()`). Start here.
2. **Classic API (advanced)** — the `*Grid` classes (`GeohashGrid`, `H3Grid`, …)
   when you need fine-grained control or are integrating into existing code.
3. **Power tools (advanced, optional)** — `GridBuilder` (fluent pipelines),
   `PrecisionSelector` (precision strategies), `MultiGridComparator`
   (cross-system comparison). Reach for these only for the specific workflow
   each enables; you never need them for everyday tasks. See
   `examples/quickstart.py` and `examples/precision_selection_example.py`.

All tiers interoperate and share the same `GridCell` objects, so you can mix
them freely.

### All Grid Systems (Classic API)

```python
from m3s import (
    GeohashGrid, MGRSGrid, H3Grid, QuadkeyGrid, S2Grid, SlippyGrid,
    CSquaresGrid, GARSGrid, MaidenheadGrid, PlusCodeGrid, What3WordsGrid
)
from shapely.geometry import Point, box
import geopandas as gpd

# Create grids with different systems
grids = {
    'Geohash': GeohashGrid(precision=5),        # ~4,892 km² cells
    'MGRS': MGRSGrid(precision=1),              # 100 km² cells
    'H3': H3Grid(resolution=7),                 # ~5.16 km² cells
    'Quadkey': QuadkeyGrid(level=12),           # ~95.73 km² cells
    'S2': S2Grid(level=10),                     # ~81.07 km² cells
    'Slippy': SlippyGrid(zoom=12),              # ~95.73 km² cells
    'C-squares': CSquaresGrid(precision=3),     # Marine data indexing
    'GARS': GARSGrid(precision=2),              # Global Area Reference System
    'Maidenhead': MaidenheadGrid(precision=3),  # Amateur radio locator
    'Plus Codes': PlusCodeGrid(precision=10),   # Open Location Codes
    'What3Words': What3WordsGrid(precision=1)   # 3-meter precision squares (only precision 1)
}

# Get cell areas
for name, grid in grids.items():
    print(f"{name}: {grid.area_km2:.2f} km² per cell")

# Get cells for NYC coordinates
lat, lon = 40.7128, -74.0060
for name, grid in grids.items():
    cell = grid.get_cell_from_point(lat, lon)
    print(f"{name}: {cell.identifier}")

# Example output:
# Geohash: 4,892.00 km² per cell
# MGRS: 100.00 km² per cell  
# H3: 5.16 km² per cell
# Quadkey: 95.73 km² per cell
# S2: 81.07 km² per cell
# Slippy: 95.73 km² per cell
#
# Geohash: dr5re
# MGRS: 18TWL8451
# H3: 871fb4662ffffff
# Quadkey: 120220012313
# S2: 89c2594
# Slippy: 12/1207/1539
```

### GeoDataFrame Integration with UTM Zones

```python
import geopandas as gpd
from m3s import H3Grid, QuadkeyGrid, SlippyGrid
from shapely.geometry import Point, box

# Create a GeoDataFrame
gdf = gpd.GeoDataFrame({
    'city': ['NYC', 'LA', 'Chicago'],
    'population': [8_336_817, 3_979_576, 2_693_976]
}, geometry=[
    Point(-74.0060, 40.7128),  # NYC
    Point(-118.2437, 34.0522), # LA  
    Point(-87.6298, 41.8781)   # Chicago
], crs="EPSG:4326")

# Intersect with any grid system - includes UTM zone information for applicable grids
grid = H3Grid(resolution=7)
result = grid.intersects(gdf)
print(f"Grid cells: {len(result)}")
print(result[['cell_id', 'utm', 'city', 'population']].head())

# Example output:
#            cell_id    utm       city  population
# 0  8828308281fffff  32618        NYC    8336817
# 1  88283096773ffff  32611         LA    3979576
# 2  8828872c0ffffff  32616    Chicago    2693976

# Web mapping grids (Quadkey, Slippy) don't include UTM zones
web_grid = SlippyGrid(zoom=12)
web_result = web_grid.intersects(gdf)
print(web_result[['cell_id', 'city']].head())
# Output:
#        cell_id       city
# 0  12/1207/1539        NYC
# 1  12/696/1582          LA
# 2  12/1030/1493    Chicago
```

### MGRS Grids with UTM Integration

```python
from m3s import MGRSGrid

# Create an MGRS grid with 1km precision
grid = MGRSGrid(precision=2)

# Get a grid cell from coordinates
cell = grid.get_cell_from_point(40.7128, -74.0060)
print(f"MGRS: {cell.identifier}")

# Intersect with GeoDataFrame - automatically includes UTM zone
result = grid.intersects(gdf)
print(result[['cell_id', 'utm']].head())
# Output shows MGRS cells with their corresponding UTM zones:
#   cell_id    utm
# 0  18TWL23  32618  # UTM Zone 18N for NYC area
```

### H3 Grids

```python
from m3s import H3Grid

# Create an H3 grid with resolution 7 (~4.5km edge length)
grid = H3Grid(resolution=7)

# Get a hexagonal cell from coordinates
cell = grid.get_cell_from_point(40.7128, -74.0060)
print(f"H3: {cell.identifier}")

# Get neighboring hexagons (6 neighbors)
neighbors = grid.get_neighbors(cell)
print(f"Neighbors: {len(neighbors)}")

# Get children at higher resolution
children = grid.get_children(cell)
print(f"Children: {len(children)}")  # Always 7 for H3

# Find intersecting cells with UTM zone information
result = grid.intersects(gdf)
print(result[['cell_id', 'utm', 'city']].head())
```

## Grid Systems

### Geohash
Hierarchical spatial data structure using Base32 encoding. Each character represents 5 bits of spatial precision.
- **Precision Levels**: 1-12
- **Cell Shape**: Rectangular
- **Use Cases**: Databases, simple spatial indexing

### MGRS (Military Grid Reference System)
Coordinate system based on UTM with standardized square cells.
- **Precision Levels**: 0-5 (100km to 1m)
- **Cell Shape**: Square
- **Use Cases**: Military, surveying, precise location reference

### H3 (Uber's Hexagonal Hierarchical Spatial Index)
Hexagonal grid system with uniform neighbor relationships and excellent area representation.
- **Resolution Levels**: 0-15
- **Cell Shape**: Hexagonal
- **Use Cases**: Spatial analysis, ride-sharing, logistics

### Quadkey (Microsoft Bing Maps)
Quadtree-based square tiles used by Microsoft Bing Maps.
- **Levels**: 1-23
- **Cell Shape**: Square
- **Use Cases**: Web mapping, tile-based applications

### S2 (Google's Spherical Geometry)
Spherical geometry cells using Hilbert curve for optimal spatial locality.
- **Levels**: 0-30
- **Cell Shape**: Curved (spherical quadrilaterals)
- **Use Cases**: Large-scale applications, global spatial indexing

### Slippy Map Tiles
Standard web map tiles used by OpenStreetMap and most web mapping services.
- **Zoom Levels**: 0-22
- **Cell Shape**: Square (in Web Mercator projection)
- **Use Cases**: Web mapping, tile servers, caching

## API Reference

### BaseGrid

All grid classes inherit from `BaseGrid`:

```python
class BaseGrid:
    # Required interface (abstract — every grid implements these)
    @property
    def area_km2(self) -> float
        """Theoretical area in km² for cells at this precision/resolution/level"""

    def get_cell_from_point(self, lat: float, lon: float) -> GridCell
    def get_cell_from_identifier(self, identifier: str) -> GridCell
    def get_neighbors(self, cell: GridCell) -> List[GridCell]
    def get_cells_in_bbox(self, min_lat: float, min_lon: float,
                         max_lat: float, max_lon: float) -> List[GridCell]

    # Optional hierarchy interface — only hierarchical grids (H3, S2,
    # Quadkey, Slippy). refine()/coarsen() raise NotImplementedError on grids
    # that do not provide these.
    def get_children(self, cell: GridCell) -> List[GridCell]
    def get_parent(self, cell: GridCell) -> Optional[GridCell]
    def get_covering_cells(self, polygon: Polygon, max_cells: int = 100) -> List[GridCell]

    # GeoDataFrame integration methods with UTM zone support
    def intersects(self, gdf: gpd.GeoDataFrame,
                  target_crs: str = "EPSG:4326") -> gpd.GeoDataFrame
```

### Parallel Processing

```python
from m3s.parallel import ParallelGridEngine, ParallelConfig

# Configure parallel processing
config = ParallelConfig(
    n_workers=4,
    chunk_size=10000
)

# Process large datasets in parallel
engine = ParallelGridEngine(config)
result = engine.intersect_parallel(grid, large_gdf)
```

### UTM Zone Integration

All grid systems now automatically include a `utm` column in their `intersects()` results:

- **MGRS**: UTM zone extracted directly from MGRS identifier
- **Geohash**: UTM zone calculated from cell centroid coordinates  
- **H3**: UTM zone calculated from hexagon centroid coordinates

The UTM column contains EPSG codes (e.g., 32614 for UTM Zone 14N, 32723 for UTM Zone 23S).

## Development

### Setup

```bash
git clone https://github.com/nkarasiak/m3s.git
cd m3s
uv pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black m3s tests examples
```

### Type Checking

```bash
mypy m3s
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Dependencies

### Required
- [Shapely](https://shapely.readthedocs.io/) - Geometric operations
- [PyProj](https://pyproj4.github.io/pyproj/) - Coordinate transformations  
- [GeoPandas](https://geopandas.org/) - Geospatial data manipulation
- [mgrs](https://pypi.org/project/mgrs/) - MGRS coordinate conversions
- [h3](https://pypi.org/project/h3/) - H3 hexagonal grid operations
- [s2sphere](https://pypi.org/project/s2sphere/) - S2 spherical geometry operations

**Notes**: 
- Geohash, Quadkey, and Slippy Map Tiles are implemented using pure Python (no external dependencies)
- S2 functionality requires the s2sphere library for proper spherical geometry calculations

## Acknowledgments

- Built for geospatial analysis and location intelligence applications
- Thanks to the maintainers of the underlying spatial libraries
