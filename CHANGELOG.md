# Changelog

All notable changes to M3S (Multi Spatial Subdivision System) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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