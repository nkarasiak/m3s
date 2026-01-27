Changelog
=========

All notable changes to M3S (Multi Spatial Subdivision System) will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

Unreleased
----------

Added
~~~~~
- Reintroduced A5 pentagonal grid system in the unified grid API

Changed
~~~~~~~
- ``precision`` is the preferred constructor argument across all grids; resolution/level/zoom aliases remain but are silent

0.4.1 - 2025-08-21
------------------

Fixed
~~~~~
- **Plus Codes Grid**: Fixed cell boundary intersection logic

  - Now correctly returns 8 cells (4 columns × 2 rows) for test areas
  - Removed incorrect inclusion of boundary-only cells that don't actually overlap
  - Improved intersection filtering to match expected spatial behavior

- **Maidenhead Grid**: Fixed missing eastern column cells in bounding box queries

  - Enhanced sampling algorithm to use 3x denser grid points
  - Now correctly finds all intersecting cells including boundary cases
  - Fixed issue where F column cells were missed due to sparse sampling
  - Now correctly returns 9 cells (3 columns × 3 rows) for test areas

Enhanced
~~~~~~~~
- **Grid Sampling Algorithms**: Improved boundary condition handling

  - Plus codes and Maidenhead grids now use more robust intersection detection
  - Better handling of floating-point precision issues in grid boundaries
  - More accurate cell discovery for bounding box queries

0.4.0 - 2025-08-21
------------------

Added
~~~~~
- **Performance & Scalability Enhancements**: Major optimization improvements for large-scale processing

  - ``cache.py`` - Comprehensive caching system with LRU cache, spatial cache, and decorators
  - ``memory.py`` - Memory-efficient processing with monitoring, lazy loading, and streaming
  - ``@cached_method`` and ``@cached_property`` decorators for expensive operations
  - ``MemoryMonitor`` class with automatic memory pressure detection and adaptive chunk sizing
  - ``LazyGeodataFrame`` for processing large geospatial files without full memory load
  - ``StreamingGridProcessor`` with memory-aware processing and automatic optimization

- **Comprehensive CSquares Grid Testing**: Test coverage increased from 9% to 98%

  - 21 new test cases covering all CSquares functionality
  - Edge case testing for error handling and boundary conditions
  - Added missing ``area_km2`` property implementation for CSquares

- **Smart Caching for Expensive Operations**:

  - Geographic coordinate lookups cached with spatial-aware key generation
  - Grid cell area calculations cached using cached_property
  - Neighbor finding operations cached to avoid repeated computation
  - UTM zone calculations cached with coordinate rounding for efficiency

Enhanced
~~~~~~~~
- **Parallel Processing Engine**: Memory-aware enhancements

  - Added ``optimize_memory`` and ``adaptive_chunking`` configuration options
  - Automatic GeoDataFrame memory optimization before processing
  - Dynamic chunk size adjustment based on memory pressure
  - Enhanced error handling for memory-constrained environments

- **GeohashGrid**: Applied caching to expensive operations

  - ``get_cell_from_point()`` now uses spatial caching
  - ``get_neighbors()`` operations cached for repeated requests

- **BaseGrid**: Enhanced with cached area calculations

  - ``area_km2`` property now uses cached_property for performance

Fixed
~~~~~
- **Parallel Processing Bugs**: Fixed critical issues in parallel integration

  - Resolved ``NameError: name 'delayed' is not defined`` in parallel processing
  - Fixed fallback test failures with proper mock handling
  - Added proper import fallbacks for missing optional dependencies

- **Memory Management**: Graceful handling of optional dependencies

  - ``psutil`` made optional with fallback implementations for memory monitoring
  - All memory features work without optional dependencies installed
  - Proper warnings when advanced features are unavailable

Performance
~~~~~~~~~~~
- **Significant Memory Reduction**: Optimized memory usage for large datasets

  - Lazy evaluation prevents unnecessary data loading
  - Automatic garbage collection during processing
  - Memory pressure monitoring with adaptive responses

- **Caching Performance**: Substantial speedup for repeated operations

  - Coordinate-based operations benefit from spatial caching
  - Area calculations cached to avoid repeated expensive projections
  - Neighbor queries cached for common access patterns

- **Streaming Efficiency**: Process datasets larger than available memory

  - Chunked processing with automatic size optimization
  - Memory-aware fallbacks for problematic data chunks
  - Streaming iterators for minimal memory footprint

Technical
~~~~~~~~~
- **New Modules**: Added two major new modules

  - ``m3s.cache`` - Caching utilities and decorators
  - ``m3s.memory`` - Memory optimization and monitoring tools

- **Enhanced Test Suite**: Added comprehensive test coverage

  - ``test_cache.py`` - 13 tests covering all caching functionality
  - ``test_csquares.py`` - 21 tests bringing CSquares to 98% coverage
  - All parallel processing tests now pass (27/27)

0.3.0 - 2025-08-21
------------------

Added
~~~~~
- **New Grid Systems**: Expanded from 3 to 6 spatial grid systems

  - ``QuadkeyGrid`` - Microsoft Bing Maps quadtree-based square tiles (levels 1-23)
  - ``S2Grid`` - Google's spherical geometry cells using Hilbert curve (levels 0-30)
  - ``SlippyGrid`` - Standard web map tiles (z/x/y format) used by OpenStreetMap (zoom 0-22)

- **Grid Area Properties**: All grid systems now support ``area_km2`` property

  - Returns theoretical area in square kilometers for cells at specified precision/resolution/level
  - Example: ``H3Grid(7).area_km2`` returns 5.16 km²

- **Parallel Processing Engine**: Comprehensive distributed computing support

  - ``ParallelGridEngine`` with threading and process backends
  - Stream processing capabilities for large datasets
  - Automatic fallbacks when specialized libraries are unavailable

- **Enhanced Examples**: Updated visualization examples

  - All 6 grid systems displayed in comprehensive comparison plots
  - Area calculations and grid characteristics documentation

Changed
~~~~~~~
- **S2 Grid Implementation**: Completely rewritten S2 implementation

  - Removed fallback implementation in favor of proper ``s2sphere`` library integration
  - Made ``s2sphere>=0.2.5`` a required dependency (was optional)
  - Fixed cell generation issues where no tiles were found

- **Example Visualizations**: Updated to 3×2 subplot layout to accommodate 6 grid systems
- **Dependencies**: Added ``s2sphere>=0.2.5`` as required dependency

Fixed
~~~~~
- S2 grid cell generation now works correctly with proper s2sphere integration
- Fixed coordinate conversion issues in S2 implementation
- Corrected S2 level 9 edge length comment (18km, not 50km)

0.2.0 - 2025-08-20
------------------

Added
~~~~~
- Example scripts demonstrating practical usage

  - ``grid_generation_example.py`` - Visualize MGRS, H3, and Geohash grids using matplotlib
  - ``utm_reprojection_example.py`` - Demonstrate UTM zone detection and accurate area calculations

Changed
~~~~~~~
- **BREAKING**: Simplified grid API by consolidating intersection methods

  - Renamed ``intersect_geodataframe()`` to ``intersects()`` across all grid systems
  - Removed ``intersect_geodataframe_aggregated()`` method
  - Removed ``intersect_polygon()`` method (functionality merged into ``intersects()``)

- Updated all examples and tests to use the new simplified API

0.1.0 - 2025-08-20
------------------

Added
~~~~~
- Initial release of M3S package
- Base grid interface with ``BaseGrid`` abstract class
- ``GridCell`` class for representing individual grid cells
- Geohash grid implementation (``GeohashGrid``)

  - Support for precision levels 1-12
  - Point-to-cell conversion
  - Neighbor finding functionality
  - Cell expansion to higher precision levels
  - Bounding box cell enumeration

- MGRS (Military Grid Reference System) grid implementation (``MGRSGrid``)

  - Support for precision levels 1-5 (10km to 1m grids)
  - UTM coordinate system integration
  - Proper polygon creation for MGRS cells
  - Neighbor finding with UTM projections

- Polygon intersection functionality for both grid types

  - ``intersect_polygon()`` method to find grid cells intersecting with Shapely polygons
  - Efficient bounding box-based filtering

- Comprehensive test suite with full coverage
- Modern Python packaging with ``pyproject.toml``

Dependencies
~~~~~~~~~~~~
- ``shapely>=2.0.0`` - For geometric operations and polygon handling
- ``pyproj>=3.4.0`` - For coordinate system transformations (MGRS)
- ``mgrs>=1.4.0`` - For MGRS coordinate conversions

Internal Implementations
~~~~~~~~~~~~~~~~~~~~~~~~
- Pure Python geohash implementation (no external dependencies)
- Custom geohash encoder/decoder with bbox and neighbors support
