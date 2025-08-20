# Changelog

All notable changes to M3S (Multi Spatial Subdivision System) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2025-08-20

### Added
- **UTM Zone Integration**: All grid systems now include UTM zone information
  - `utm` column in `intersect_geodataframe()` results containing EPSG codes
  - MGRS: UTM zone extracted directly from MGRS identifier
  - Geohash: UTM zone calculated from cell centroid coordinates
  - H3: UTM zone calculated from hexagon centroid coordinates
  - Automatic handling of special UTM cases (Norway, Svalbard)

### Changed  
- Updated documentation to focus on core spatial functionality
- Simplified package description and removed hierarchical references

## [0.2.0] - 2025-08-20

### Added
- **GeoPandas Integration**: Native support for GeoDataFrames with automatic CRS transformation
  - `intersect_geodataframe()` method for all grid systems
  - `intersect_geodataframe_aggregated()` method for unique cell analysis
  - Automatic coordinate reference system (CRS) handling
  - Preserves original GeoDataFrame data and attributes
- H3 (Uber's Hexagonal Hierarchical Spatial Index) grid system support
  - Resolution levels 0-15 with hexagonal cells
  - Hierarchical operations (parent/children relationships)
  - Compact/uncompact operations for optimization
  - Neighbor finding (always 6 neighbors for hexagons)
  - Global uniform coverage with minimal distortion
- MGRS precision 0 support for 100km × 100km grid squares  
- Comprehensive precision documentation with detailed tables
- Performance and selection guidelines for choosing grid systems
- Equivalent precision mapping between all grid systems

### Changed
- MGRS precision range expanded from 1-5 to 0-5
- Updated documentation with complete precision specifications
- Enhanced package description and metadata

### Dependencies Added
- `geopandas>=0.13.0` - For GeoDataFrame support and CRS handling
- `h3>=3.7.0` - For H3 hexagonal grid operations

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