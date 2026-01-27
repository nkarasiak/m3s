# M3S - Multi Spatial Subdivision System

M3S is a unified Python package for working with hierarchical spatial grid systems. It provides a consistent, modern API for Geohash, MGRS, H3, Quadkey, S2, Slippy Map tiles, and more.

## Features

- **Multiple Grid Systems**: Geohash, MGRS, H3, Quadkey, S2, Slippy, C-squares, GARS, Maidenhead, Plus Code, What3Words-style
- **Lazy Cell Geometry**: Cells store bounds; geometry is built only when needed
- **GeoPandas Integration**: Efficient intersections with STRtree acceleration
- **Unified API**: `cell`, `from_id`, `neighbors`, `cells_in_bbox`, `intersects`
- **Parallel Processing**: thread/process backends for large-scale intersections
- **Modern Python**: Python 3.12+ with type hints

## Installation

```bash
pip install m3s
```

For development:

```bash
git clone https://github.com/yourusername/m3s.git
cd m3s
uv pip install -e ".[dev]"
```

## Quick Start

### Core API

```python
import m3s
from m3s import GeohashGrid, H3Grid, SlippyGrid

# Create grids (new entrypoint or direct classes)
geohash = m3s.grid("geohash", precision=5)
h3 = m3s.grid("h3", precision=7)
slippy = m3s.grid("slippy", precision=12)

# Get a cell from a point
cell = geohash.cell(40.7128, -74.0060)
print(cell.id, cell.bbox)

# Neighbors
neighbors = h3.neighbors(cell)

# Cells in a bounding box (min_lon, min_lat, max_lon, max_lat)
bbox = (-74.2, 40.6, -73.7, 40.9)
slippy_cells = slippy.cells_in_bbox(bbox)
```

### Precision Selection

```python
from m3s import precision

# Natural language target size
choice = precision.best("h3", target="500m")
grid = m3s.grid("h3", precision=choice.precision)
```

### GeoDataFrame Intersections

```python
import geopandas as gpd
from shapely.geometry import Point
from m3s import H3Grid

# GeoDataFrame
cities = gpd.GeoDataFrame(
    {
        "city": ["NYC", "LA", "Chicago"],
        "population": [8_336_817, 3_979_576, 2_693_976],
    },
    geometry=[
        Point(-74.0060, 40.7128),
        Point(-118.2437, 34.0522),
        Point(-87.6298, 41.8781),
    ],
    crs="EPSG:4326",
)

grid = H3Grid(precision=7)
result = grid.intersects(cities)
print(result[["cell_id", "city", "population"]].head())
```

### Parallel Processing

```python
from m3s.parallel import ParallelGridEngine, ParallelConfig
from m3s import H3Grid

config = ParallelConfig(use_processes=True, n_workers=4, chunk_size=10000)
engine = ParallelGridEngine(config)
result = engine.intersect_parallel(H3Grid(precision=7), large_gdf)
```

## Grid Systems

- **Geohash**: base32 string grid with rectangular cells; great for indexing and prefix queries.
- **MGRS**: UTM/UPS-based square grid used in military and surveying workflows.
- **H3**: mostly-hexagonal global grid with strong neighbor structure for analytics.
- **A5**: pentagonal DGGS for low-distortion global coverage.
- **Quadkey**: quadtree tiles designed for web maps and tile pyramids.
- **S2**: spherical geometry cells with excellent spatial locality.
- **Slippy**: standard Web Mercator tiles (z/x/y) for mapping pipelines.
- **C-squares**: hierarchical lat/lon grid common in marine datasets.
- **GARS**: aviation/military global area reference system.
- **Maidenhead**: ham-radio locator grid with human-friendly codes.
- **Plus Code**: open, compact location codes for address-free referencing.
- **What3Words-style**: fixed ~3m squares with human-friendly identifiers (approximation).

## API Reference (New)

```python
class GridProtocol:
    name: str
    precision: int

    def cell(self, lat: float, lon: float) -> Cell
    def from_id(self, cell_id: str | int) -> Cell
    def neighbors(self, cell: Cell) -> Sequence[Cell]
    def cells_in_bbox(self, bbox: tuple[float, float, float, float]) -> Sequence[Cell]
    def cover(self, geometry) -> Sequence[Cell]

    @property
    def area_km2(self) -> float

class Cell:
    id: str | int
    precision: int
    bbox: tuple[float, float, float, float]
    polygon: Polygon  # lazy
    area_km2: float
```

## Migration Guide

Old API -> New API

- `grid.get_cell_from_point(lat, lon)` -> `grid.cell(lat, lon)`
- `grid.get_cell_from_identifier(id)` -> `grid.from_id(id)`
- `grid.get_neighbors(cell)` -> `grid.neighbors(cell)`
- `grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)` ->
  `grid.cells_in_bbox((min_lon, min_lat, max_lon, max_lat))`
- `grid.intersects(gdf)` -> `grid.cover(geometry)` or `grid.intersects(gdf)` (wrapper)
- `GridCell.identifier` -> `Cell.id`
- `GridCell.polygon` -> `Cell.polygon` (same behavior, lazy now)

Breaking changes

- `BaseGrid` and `GridCell` removed.
- A5 modules removed.
- `MultiResolutionGrid` now takes a `grid_factory` callable instead of a grid instance.

Example conversion

```python
# Old
cell = grid.get_cell_from_point(lat, lon)

# New
cell = grid.cell(lat, lon)
```

## Development

```bash
uv run pytest
uv run black m3s tests examples
uv run mypy m3s
```

## License

MIT

