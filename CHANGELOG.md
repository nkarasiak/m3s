# Changelog

All notable changes to M3S (Multi Spatial Subdivision System) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2025-08-21

### Added
- **New Grid Systems**: Expanded from 3 to 6 spatial grid systems
  - `QuadkeyGrid` - Microsoft Bing Maps quadtree-based square tiles (levels 1-23)
  - `S2Grid` - Google's spherical geometry cells using Hilbert curve (levels 0-30)
  - `SlippyGrid` - Standard web map tiles (z/x/y format) used by OpenStreetMap (zoom 0-22)
- **Grid Area Properties**: All grid systems now support `area_km2` property
  - Returns theoretical area in square kilometers for cells at specified precision/resolution/level
  - Example: `H3Grid(7).area_km2` returns 5.16 km²
- **Parallel Processing Engine**: Comprehensive distributed computing support
  - `ParallelGridEngine` with Dask, GPU (RAPIDS), and threading backends
  - Stream processing capabilities for large datasets
  - Automatic fallbacks when specialized libraries are unavailable
- **Enhanced Examples**: Updated visualization examples
  - All 6 grid systems displayed in comprehensive comparison plots
  - Area calculations and grid characteristics documentation

### Changed
- **S2 Grid Implementation**: Completely rewritten S2 implementation
  - Removed fallback implementation in favor of proper `s2sphere` library integration
  - Made `s2sphere>=0.2.5` a required dependency (was optional)
  - Fixed cell generation issues where no tiles were found
- **Example Visualizations**: Updated to 3×2 subplot layout to accommodate 6 grid systems
- **Dependencies**: Added `s2sphere>=0.2.5` as required dependency

### Fixed
- S2 grid cell generation now works correctly with proper s2sphere integration
- Fixed coordinate conversion issues in S2 implementation
- Corrected S2 level 9 edge length comment (18km, not 50km)

## [0.2.0] - 2025-08-20

### Added
- Example scripts demonstrating practical usage
  - `grid_generation_example.py` - Visualize MGRS, H3, and Geohash grids using matplotlib
  - `utm_reprojection_example.py` - Demonstrate UTM zone detection and accurate area calculations

### Changed
- **BREAKING**: Simplified grid API by consolidating intersection methods
  - Renamed `intersect_geodataframe()` to `intersects()` across all grid systems
  - Removed `intersect_geodataframe_aggregated()` method
  - Removed `intersect_polygon()` method (functionality merged into `intersects()`)
- Updated all examples and tests to use the new simplified API

## [0.1.0] - 2025-08-20

### Added
- Initial release of M3S package
- Base grid interface with `BaseGrid` abstract class
- `GridCell` class for representing individual grid cells
- Geohash grid implementation (`GeohashGrid`)
  - Support for precision levels 1-12
  - Point-to-cell conversion
  - Neighbor finding functionality
  - Cell expansion to higher precision levels
  - Bounding box cell enumeration
- MGRS (Military Grid Reference System) grid implementation (`MGRSGrid`)
  - Support for precision levels 1-5 (10km to 1m grids)
  - UTM coordinate system integration
  - Proper polygon creation for MGRS cells
  - Neighbor finding with UTM projections
- Polygon intersection functionality for both grid types
  - `intersect_polygon()` method to find grid cells intersecting with Shapely polygons
  - Efficient bounding box-based filtering
- Comprehensive test suite with full coverage
- Modern Python packaging with `pyproject.toml`

### Dependencies
- `shapely>=2.0.0` - For geometric operations and polygon handling
- `pyproj>=3.4.0` - For coordinate system transformations (MGRS)
- `mgrs>=1.4.0` - For MGRS coordinate conversions

### Internal Implementations
- Pure Python geohash implementation (no external dependencies)
- Custom geohash encoder/decoder with bbox and neighbors support