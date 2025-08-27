# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

M3S (Multi Spatial Subdivision System) is a Python package that provides a unified interface for working with hierarchical spatial grid systems. It supports 10 different grid systems: Geohash, MGRS, H3, Quadkey, S2, Slippy Map tiles, C-squares, GARS, Maidenhead, Plus Codes, and What3Words.

**New Grid System Enhancements (Latest):**
- **Grid Conversion Utilities**: Convert between different grid systems with multiple methods (centroid, overlap, containment)
- **Relationship Analysis**: Analyze spatial relationships between grid cells (adjacency, containment, overlap)
- **Multi-Resolution Operations**: Work with multiple precision levels simultaneously for hierarchical analysis
- **What3Words Integration**: 3-meter precision grid system integration

## Development Commands

### Testing
```bash
pytest                    # Run all tests
pytest tests/test_*.py    # Run specific test file
pytest -v                 # Verbose output
pytest --cov=m3s          # Run with coverage
```

### Code Quality
```bash
black m3s tests examples       # Format code
ruff check m3s tests examples  # Lint code  
ruff check --fix m3s tests examples  # Auto-fix linting issues
mypy m3s                       # Type checking
isort m3s tests examples       # Sort imports
```

### Documentation
```bash
cd docs
make html              # Build HTML documentation
make clean             # Clean build directory
sphinx-build . _build  # Alternative build command
```

### Development Installation
```bash
pip install -e ".[dev]"      # Install with development dependencies
pip install -e ".[parallel]" # Install with parallel processing support
pip install -e ".[gpu]"      # Install with GPU acceleration support
```

## Architecture Overview

### Core Architecture
The package follows a plugin-based architecture with a common base class (`BaseGrid`) that all grid systems implement. This provides a unified API across different spatial indexing systems.

**Key Components:**
- `BaseGrid` (m3s/base.py): Abstract base class defining the common interface
- `GridCell` (m3s/base.py): Represents individual grid cells with identifier, polygon, and precision
- Individual grid implementations: GeohashGrid, MGRSGrid, H3Grid, QuadkeyGrid, S2Grid, SlippyGrid, etc.

### Grid System Modules
Each grid system is implemented in its own module:
- `geohash.py` - Base32-encoded hierarchical spatial indexing
- `mgrs.py` - Military Grid Reference System (UTM-based)
- `h3.py` - Uber's hexagonal hierarchical spatial index
- `quadkey.py` - Microsoft Bing Maps quadtree tiles
- `s2.py` - Google's spherical geometry cells
- `slippy.py` - Standard web map tiles (OpenStreetMap)
- `csquares.py` - C-squares marine data indexing
- `gars.py` - Global Area Reference System
- `maidenhead.py` - Amateur radio grid locator system
- `pluscode.py` - Open Location Codes (Plus Codes)
- `what3words.py` - What3Words-style 3-meter precision squares

### Grid System Enhancement Modules
New modules for enhanced functionality:
- `conversion.py` - Grid conversion utilities and cross-system operations
- `relationships.py` - Spatial relationship analysis between grid cells
- `multiresolution.py` - Multi-resolution grid operations and hierarchical analysis

### Performance and Memory Management
- `cache.py` - Caching system for spatial calculations and UTM projections
- `memory.py` - Memory monitoring, lazy loading, and streaming processors for large datasets
- `parallel.py` - Distributed computing with Dask, GPU acceleration with RAPIDS/CuPy

### UTM Integration
The system automatically calculates and includes UTM zone information for optimal spatial analysis. UTM zones are determined from cell centroids and cached for performance.

## Testing Structure

Tests are organized by grid system and functionality in `tests/` directory:
- Each grid system has its own test file (e.g., `test_geohash.py`, `test_h3.py`)
- `test_geodataframe.py` - GeoPandas integration tests
- `test_parallel.py` - Parallel processing tests
- `test_cache.py` - Caching system tests
- `test_what3words.py` - What3Words grid system tests
- `test_conversion.py` - Grid conversion utility tests
- `test_relationships.py` - Spatial relationship analysis tests
- `test_multiresolution.py` - Multi-resolution operation tests

## Development Guidelines

### Code Style
- Uses Black for code formatting (line length: 88)
- Ruff for linting with strict settings
- MyPy for type checking with strict configuration
- NumPy-style docstrings
- isort for import sorting

### Grid System Implementation
When implementing new grid systems:
1. Inherit from `BaseGrid` class
2. Implement all abstract methods
3. Follow existing patterns for precision/resolution parameters
4. Include area calculations via `area_km2` property
5. Support GeoPandas integration with UTM zone information
6. Add comprehensive test coverage

### Performance Considerations
- Use caching for expensive spatial calculations
- Leverage the memory management utilities for large datasets
- Consider GPU acceleration paths when applicable
- Profile memory usage with the built-in MemoryMonitor

### Documentation
- Examples are auto-generated from `examples/` directory using Sphinx Gallery
- Documentation built with PyData Sphinx Theme
- API documentation auto-generated from docstrings
- New example `grid_enhancements_example.py` demonstrates all grid system enhancements

## New Features Usage

### Grid Conversion
```python
from m3s import convert_cell, create_conversion_table, list_grid_systems

# Convert between grid systems
geohash_cell = GeohashGrid(5).get_cell_from_point(40.7128, -74.0060)
h3_cell = convert_cell(geohash_cell, 'h3', method='centroid')

# Create conversion table for a region
conversion_table = create_conversion_table('geohash', 'h3', bounds)
```

### Relationship Analysis
```python
from m3s import analyze_relationship, find_adjacent_cells, create_adjacency_matrix

# Analyze spatial relationships
relationship = analyze_relationship(cell1, cell2)
adjacent_cells = find_adjacent_cells(target_cell, candidate_cells)
adjacency_matrix = create_adjacency_matrix(cells)
```

### Multi-Resolution Operations
```python
from m3s import create_multiresolution_grid, get_hierarchical_cells

# Create multi-resolution grid
multi_grid = create_multiresolution_grid(base_grid, [4, 5, 6, 7])
hierarchical = get_hierarchical_cells(multi_grid, point)
adaptive_grid = create_adaptive_grid(base_grid, bounds, levels)
```

### What3Words Grid
```python
from m3s import What3WordsGrid

# Use What3Words-style 3-meter grid
w3w_grid = What3WordsGrid()
cell = w3w_grid.get_cell_from_point(40.7128, -74.0060)
neighbors = w3w_grid.get_neighbors(cell)  # 8 neighbors
```