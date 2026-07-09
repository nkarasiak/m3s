# M3S - Multi Spatial Subdivision System

> [!WARNING]
> This project is a vibe-coded experiment built entirely with [Claude Code](https://claude.com/claude-code) as a test of AI-assisted development. It is **not production-tested or audited**. For a mature, production-grade unified grid library, use [**vgrid**](https://github.com/opengeoshub/vgrid) instead.

A unified package for working with hierarchical spatial grid systems in **Python** and **JavaScript** (via WASM). Both bindings call one shared Rust core, so a cell encoded in one language decodes identically in the other. M3S (Multi Spatial Subdivision System) provides a consistent interface for working with different spatial indexing systems including Geohash, MGRS, H3, Quadkey, S2, Slippy Map tiles, C-squares, GARS, Maidenhead, Plus Codes, EA-Quad, rHEALPix, and A5.

## Features

### Direct grid access
- **🎯 No instantiation needed**: just `m3s.H3`, `m3s.Geohash`, etc.
- **🌐 Universal Geometry**: Single `from_geometry()` handles points, polygons, bboxes, GeoDataFrames
- **🔍 Smart Precision**: Auto-select optimal precision or choose by use case, area, or cell count
- **🔄 Easy Conversion**: Convert between grids with `.to_h3()`, `.to_geohash()`, etc.
- **📦 Powerful Collections**: Filter, map, export with `GridCellCollection`

### Core Capabilities
- **13 Grid Systems**: Geohash, MGRS, H3, Quadkey, S2, Slippy, C-squares, GARS, Maidenhead, Plus Codes, EA-Quad, rHEALPix, A5
- **Area Calculations**: All grids support `area_km2` property
- **GeoPandas Integration**: Native GeoDataFrame support with automatic CRS transformation
- **UTM Zone Integration**: Automatic UTM zone detection and inclusion
- **Polygon Intersection**: Find grid cells intersecting any Shapely polygon or GeoDataFrame
- **Hierarchical Operations**: Parent/child relationships and multi-resolution analysis
- **Neighbor Finding**: Get neighboring cells across all grid systems
- **Parallel Processing**: Threaded parallelism and streaming for large datasets
- **Modern Python**: Type hints, comprehensive documentation and test suite

## Installation

**Python** — from PyPI:

```bash
uv pip install m3s   # or: pip install m3s
```

**JavaScript** — from npm:

```bash
npm install @nkarasiak/m3s
```

The npm package bundles both a Node (CommonJS WASM) and a browser (ESM WASM)
build; the right one is selected automatically through the `exports` map. See
[bindings/js/README.md](bindings/js/README.md) for the JS API and how to build
from source.

For development:

```bash
git clone https://github.com/nkarasiak/m3s.git
cd m3s
uv sync          # create the dev environment (.venv) from uv.lock
```

## Quick Start

M3S gives direct access to grid systems, auto-precision selection, and universal geometry handling:

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
# Other use cases: 'global', 'continental', 'country', 'region',
#                  'city', 'neighborhood', 'street', 'building', 'room'

# Dynamic, config-driven grid access by name
grid = m3s.grid('h3', precision=7)       # -> same wrapper as m3s.H3
print(m3s.grids())                       # ['csquares', 'eaquad', 'gars', 'h3', ...]

# Visualize straight from a collection (delegates to GeoPandas/folium)
cells.explore()                          # interactive Leaflet map
cells.plot(edgecolor='black')            # static matplotlib axes

# Persist and reload (round-trips through ids or a vector file)
cells.save('cells.geojson')
same = m3s.H3.from_ids(cells.to_ids())   # ids -> wrapper-aware collection
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
- `m3s.EAQuad` - Equal-area quadtree (power-of-two km cells)
- `m3s.RHEALPix` - rHEALPix equal-area DGGS (aperture 9)
- `m3s.A5` - Pentagonal equal-area DGGS

> **Coordinate order:** M3S uses GIS-native **(lon, lat)** / (x, y)
> order for coordinate tuples — matching shapely, geopandas and pyproj.
> `GridCell.bounds`, `GridCell.centroid` and `from_bbox` all follow the same
> order, so `grid.from_bbox(collection.bounds)` round-trips correctly.

### JavaScript

The JS API mirrors the Python facade in camelCase and produces identical cells.
The wrapper is thin — polygon fill, precision strategies, GeoPandas export and
cross-grid conversion stay Python-only.

```js
import * as m3s from "@nkarasiak/m3s";
await m3s.ready();                                   // awaits WASM init (no-op on Node)

// Direct grid access — (lon, lat, precision)
const cell = m3s.Geohash.fromPoint(-74.0060, 40.7128, 6);
console.log(`Cell: ${cell.id}, Area: ${cell.areaKm2.toFixed(2)} km²`);

// Cells across a bounding box  [minLon, minLat, maxLon, maxLat]
const cells = m3s.H3.fromBbox([-74.1, 40.7, -73.9, 40.8], 8);
console.log(`${cells.length} cells`, cells.toIds());
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

## Development

### Setup

```bash
git clone https://github.com/nkarasiak/m3s.git
cd m3s
uv sync          # create the dev environment (.venv) from uv.lock
```

### Running Tests

```bash
uv run pytest
```

### Code Formatting

```bash
uv run black m3s tests examples
```

### Type Checking

```bash
uv run mypy m3s
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
