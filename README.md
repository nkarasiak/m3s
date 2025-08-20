# M3S - Multi Spatial Subdivision System

A unified Python package for working with hierarchical spatial grid systems. M3S (Multi Spatial Subdivision System) provides a consistent interface for working with different spatial indexing systems including Geohash, MGRS (Military Grid Reference System), H3 hexagonal grids, and more.

## Features

- **Multiple Grid Systems**: Support for Geohash, MGRS, H3 spatial indexing systems
- **GeoPandas Integration**: Native support for GeoDataFrames with automatic CRS transformation
- **UTM Zone Integration**: Automatic UTM zone detection and inclusion for optimal spatial analysis
- **Polygon Intersection**: Find grid cells that intersect with any Shapely polygon or GeoDataFrame
- **Hierarchical Operations**: Work with different precision levels and resolutions
- **Neighbor Finding**: Get neighboring grid cells across all supported systems
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

### Geohash Grids

```python
from m3s import GeohashGrid
from shapely.geometry import Polygon

# Create a geohash grid with precision 5
grid = GeohashGrid(precision=5)

# Get a grid cell from coordinates (New York City)
cell = grid.get_cell_from_point(40.7128, -74.0060)
print(f"Geohash: {cell.identifier}")  # e.g., "dr5ru"

# Find neighboring cells
neighbors = grid.get_neighbors(cell)
print(f"Number of neighbors: {len(neighbors)}")

# Find grid cells intersecting with a polygon
polygon = Polygon([
    (-74.1, 40.7), (-74.0, 40.7), 
    (-74.0, 40.8), (-74.1, 40.8), 
    (-74.1, 40.7)
])
intersecting_cells = grid.intersect_polygon(polygon)
print(f"Intersecting cells: {len(intersecting_cells)}")
```

### GeoDataFrame Integration with UTM Zones

```python
import geopandas as gpd
from m3s import GeohashGrid, MGRSGrid, H3Grid
from shapely.geometry import Point, box

# Create a GeoDataFrame with different CRS
gdf = gpd.GeoDataFrame({
    'city': ['NYC', 'LA', 'Chicago'],
    'population': [8_336_817, 3_979_576, 2_693_976]
}, geometry=[
    Point(-74.0060, 40.7128),  # NYC
    Point(-118.2437, 34.0522), # LA  
    Point(-87.6298, 41.8781)   # Chicago
], crs="EPSG:4326")

# Intersect with any grid system - includes UTM zone information
grid = H3Grid(resolution=7)
result = grid.intersect_geodataframe(gdf)
print(f"Grid cells: {len(result)}")
print(result[['cell_id', 'utm', 'city', 'population']].head())

# UTM column contains the best UTM EPSG code for each cell
# Example output:
#            cell_id    utm       city  population
# 0  8828308281fffff  32618        NYC    8336817
# 1  88283096773ffff  32611         LA    3979576
# 2  8828872c0ffffff  32616    Chicago    2693976

# Works with any CRS - automatically transforms and provides UTM zones
gdf_utm = gdf.to_crs("EPSG:32633")  # UTM Zone 33N
result_utm = grid.intersect_geodataframe(gdf_utm)
print(f"Same results with different CRS: {len(result_utm)}")
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

Geohash is a hierarchical spatial data structure that subdivides space into buckets of grid shape. It uses a Base32 encoding system where each character represents 5 bits of spatial precision.

**Precision Levels**: 1-12

### MGRS (Military Grid Reference System)

MGRS is a coordinate system based on the UTM coordinate system. It provides a standardized way to reference locations using a grid-based method with fixed square cells.

**Precision Levels**: 0-5

### H3 (Uber's Hexagonal Hierarchical Spatial Index)

H3 is a hexagonal grid system developed by Uber for spatial indexing. It uses a hierarchical structure with hexagonal cells that provide more uniform neighbor relationships and better area representation than square grids.

**Resolution Levels**: 0-15

## API Reference

### BaseGrid

All grid classes inherit from `BaseGrid`:

```python
class BaseGrid:
    def get_cell_from_point(self, lat: float, lon: float) -> GridCell
    def get_cell_from_identifier(self, identifier: str) -> GridCell
    def get_neighbors(self, cell: GridCell) -> List[GridCell]
    def get_cells_in_bbox(self, min_lat: float, min_lon: float, 
                         max_lat: float, max_lon: float) -> List[GridCell]
    def intersect_polygon(self, polygon: Polygon) -> List[GridCell]
    
    # GeoDataFrame integration methods with UTM zone support
    def intersect_geodataframe(self, gdf: gpd.GeoDataFrame, 
                              target_crs: str = "EPSG:4326") -> gpd.GeoDataFrame
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

- [Shapely](https://shapely.readthedocs.io/) - Geometric operations
- [PyProj](https://pyproj4.github.io/pyproj/) - Coordinate transformations  
- [GeoPandas](https://geopandas.org/) - Geospatial data manipulation
- [mgrs](https://pypi.org/project/mgrs/) - MGRS coordinate conversions
- [h3](https://pypi.org/project/h3/) - H3 hexagonal grid operations

**Note**: Geohash functionality is implemented using a pure Python implementation included with the package, requiring no external geohash dependencies.

## Acknowledgments

- Built for geospatial analysis and location intelligence applications
- Thanks to the maintainers of the underlying spatial libraries