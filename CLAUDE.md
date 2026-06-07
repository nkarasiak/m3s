# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

M3S (Multi Spatial Subdivision System) is a Python package that provides a unified interface for working with hierarchical spatial grid systems. It supports 12 different grid systems: Geohash, MGRS, H3, Quadkey, S2, Slippy Map tiles, C-squares, GARS, Maidenhead, Plus Codes, EA-Quad, and A5.

**Grid System Enhancements:**
- **Grid Conversion Utilities**: Convert between different grid systems with multiple methods (centroid, overlap, containment)
- **Relationship Analysis**: Analyze spatial relationships between grid cells (adjacency, containment, overlap)
- **Multi-Resolution Operations**: Work with multiple precision levels simultaneously for hierarchical analysis

## Development Commands

This project uses **uv** for dependency and environment management. All commands
run inside the uv-managed dev environment: run `uv sync` once to create it
(`.venv`, interpreter pinned by `.python-version`), then prefix tools with
`uv run`.

### Development Installation
```bash
uv sync                                   # Create/refresh the dev environment (.venv) from uv.lock
uv sync --no-default-groups --extra test  # Test-only environment
uv sync --no-default-groups --extra docs  # Docs/gallery build environment
```

### Testing
```bash
uv run pytest                    # Run all tests
uv run pytest tests/test_*.py    # Run specific test file
uv run pytest -v                 # Verbose output
uv run pytest --cov=m3s          # Run with coverage
```

### Code Quality
```bash
uv run black m3s tests examples       # Format code
uv run ruff check m3s tests examples  # Lint code
uv run ruff check --fix m3s tests examples  # Auto-fix linting issues
uv run mypy m3s                       # Type checking
uv run isort m3s tests examples       # Sort imports
```

### Documentation
```bash
cd docs
uv run make html                           # Build HTML documentation
uv run make clean                          # Clean build directory
uv run sphinx-build -b html . _build/html  # Alternative build command
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

> **Note:** A5 (`m3s/a5.py`) is a supported grid backed by the shared
> [`m3s_core`](https://a5geo.org/) Rust core (the `a5` crate, same source as
> `pya5`) — a thin `BaseGrid` adapter that delegates the pentagonal/dodecahedral
> math to the core. Earlier hand-rolled A5 experiments survive only under
> `m3s/archive/` and are excluded from the built package, linting and type
> checking; treat those as archived, not the A5 grid.

## Testing Structure

Tests are organized by grid system and functionality in `tests/` directory:
- Each grid system has its own test file (e.g., `test_geohash.py`, `test_h3.py`)
- `test_geodataframe.py` - GeoPandas integration tests
- `test_parallel.py` - Parallel processing tests
- `test_cache.py` - Caching system tests
- `test_conversion.py` - Grid conversion utility tests
- `test_relationships.py` - Spatial relationship analysis tests
- `test_multiresolution.py` - Multi-resolution operation tests

Run specific tests:
```bash
uv run pytest tests/test_geohash.py          # Test single grid system
uv run pytest tests/test_h3.py -v            # Test H3 with verbose output
uv run pytest tests/test_conversion.py::test_convert_cell  # Test specific function
```

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
- Documentation built with PyData Sphinx Theme (switched from sphinx-material)
- API documentation auto-generated from docstrings with NumPy-style conventions
- Key examples:
  - `grid_enhancements_example.py` - Grid conversion, relationships, multi-resolution
  - `new_grids_example.py` - C-squares, GARS, Maidenhead, Plus Codes
  - `quadkey_s2_example.py` - Web mapping grids
  - `utm_reprojection_example.py` - UTM zone integration

Build documentation:
```bash
cd docs
uv run make html       # Output in docs/_build/html
uv run make clean      # Clean build artifacts
```

## Key Features Usage

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

## Development Workflow

### Before Committing
Always run code quality checks:
```bash
uv run black m3s tests examples              # Format code
uv run isort m3s tests examples               # Sort imports
uv run ruff check --fix m3s tests examples    # Fix linting issues
uv run mypy m3s                               # Type checking
uv run pytest                                 # Run all tests
```