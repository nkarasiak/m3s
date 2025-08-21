# M3S - Multi Spatial Subdivision System

A unified Python package for working with hierarchical spatial grid systems. M3S (Multi Spatial Subdivision System) provides a consistent interface for working with different spatial indexing systems including Geohash, MGRS, H3, Quadkey, S2, and Slippy Map tiles.

## Features

- **6 Grid Systems**: Support for Geohash, MGRS, H3, Quadkey, S2, and Slippy Map tiles
- **Area Calculations**: All grids support `area_km2` property for theoretical cell areas
- **GeoPandas Integration**: Native support for GeoDataFrames with automatic CRS transformation
- **UTM Zone Integration**: Automatic UTM zone detection and inclusion for optimal spatial analysis
- **Polygon Intersection**: Find grid cells that intersect with any Shapely polygon or GeoDataFrame
- **Hierarchical Operations**: Work with different precision levels and resolutions
- **Neighbor Finding**: Get neighboring grid cells across all supported systems
- **Parallel Processing**: Distributed computing with Dask, GPU acceleration, and streaming support
- **Unified Interface**: Consistent API across all grid systems
- **Modern Python**: Built with modern Python packaging and comprehensive type hints
- **Comprehensive Testing**: Full test coverage with pytest

## Installation

```bash
pip install m3s
```

For development:

```bash
git clone https://github.com/yourusername/m3s.git
cd m3s
pip install -e ".[dev]"
```

## Quick Start

### All Grid Systems

```python
from m3s import GeohashGrid, MGRSGrid, H3Grid, QuadkeyGrid, S2Grid, SlippyGrid
from shapely.geometry import Point, box
import geopandas as gpd

# Create grids with different systems
grids = {
    'Geohash': GeohashGrid(precision=5),        # ~4,892 km² cells
    'MGRS': MGRSGrid(precision=1),              # 100 km² cells  
    'H3': H3Grid(resolution=7),                 # ~5.16 km² cells
    'Quadkey': QuadkeyGrid(level=12),           # ~95.73 km² cells
    'S2': S2Grid(level=10),                     # ~81.07 km² cells
    'Slippy': SlippyGrid(zoom=12)               # ~95.73 km² cells
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
# Geohash: 5,892.00 km² per cell
# MGRS: 100.00 km² per cell  
# H3: 5.16 km² per cell
# Quadkey: 95.73 km² per cell
# S2: 81.07 km² per cell
# Slippy: 95.73 km² per cell
#
# Geohash: dr5ru
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
result = grid.intersect_geodataframe(gdf)
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
result = grid.intersect_geodataframe(gdf)
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
    @property
    def area_km2(self) -> float
        """Theoretical area in km² for cells at this precision/resolution/level"""
    
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell
    def get_cell_from_identifier(self, identifier: str) -> GridCell
    def get_neighbors(self, cell: GridCell) -> List[GridCell]
    def get_children(self, cell: GridCell) -> List[GridCell]
    def get_parent(self, cell: GridCell) -> Optional[GridCell]
    def get_cells_in_bbox(self, min_lat: float, min_lon: float, 
                         max_lat: float, max_lon: float) -> List[GridCell]
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
    use_dask=True,
    use_gpu=True,
    n_workers=4,
    chunk_size=10000
)

# Process large datasets in parallel
engine = ParallelGridEngine(config)
result = engine.intersect_parallel(grid, large_gdf)
```

### UTM Zone Integration

All grid systems now automatically include a `utm` column in their `intersect_geodataframe()` results:

- **MGRS**: UTM zone extracted directly from MGRS identifier
- **Geohash**: UTM zone calculated from cell centroid coordinates  
- **H3**: UTM zone calculated from hexagon centroid coordinates

The UTM column contains EPSG codes (e.g., 32614 for UTM Zone 14N, 32723 for UTM Zone 23S).

## Development

### Setup

```bash
git clone https://github.com/yourusername/m3s.git
cd m3s
pip install -e ".[dev]"
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

### Optional (for parallel processing)
- [dask](https://dask.org/) - Distributed computing (`pip install m3s[parallel]`)
- [cupy](https://cupy.dev/) - GPU acceleration (`pip install m3s[gpu]`)

**Notes**: 
- Geohash, Quadkey, and Slippy Map Tiles are implemented using pure Python (no external dependencies)
- S2 functionality requires the s2sphere library for proper spherical geometry calculations

## Acknowledgments

- Built for geospatial analysis and location intelligence applications
- Thanks to the maintainers of the underlying spatial libraries