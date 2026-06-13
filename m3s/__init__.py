"""
M3S - Multi Spatial Subdivision System.

A unified Python package for working with hierarchical spatial grid systems,
including grid conversion utilities, relationship analysis, and multi-resolution
operations.

The default entry point (the "golden path") is the grid-singleton
API, which uses GIS-native (lon, lat) coordinate order::

    import m3s
    cell = m3s.H3.from_geometry((-74.0060, 40.7128))   # (lon, lat)
    cells = m3s.H3.from_geometry(polygon)

The classic ``*Grid`` classes and the advanced ``GridBuilder`` /
``PrecisionSelector`` / ``MultiGridComparator`` tools are optional; see the
README "Which API should I use?" section.
"""

# Modern API
from .a5 import A5Grid
from .api import (
    AreaCalculator,
    GridBuilder,
    GridCellCollection,
    GridQueryResult,
    GridWrapper,
    MultiGridComparator,
    PerformanceProfiler,
    PrecisionFinder,
    PrecisionRecommendation,
    PrecisionSelector,
)
from .base import BaseGrid

# New grid system enhancements
from .conversion import (
    GridConverter,
    convert_cell,
    convert_cells,
    create_conversion_table,
    get_equivalent_precision,
    list_grid_systems,
)
from .csquares import CSquaresGrid
from .eaquad import EAQuadGrid
from .gars import GARSGrid
from .geohash import GeohashGrid
from .h3 import H3Grid
from .maidenhead import MaidenheadGrid
from .memory import (
    LazyGeodataFrame,
    MemoryMonitor,
    StreamingGridProcessor,
    estimate_memory_usage,
    optimize_geodataframe_memory,
)
from .mgrs import MGRSGrid
from .multiresolution import (
    MultiResolutionGrid,
    ResolutionLevel,
    create_adaptive_grid,
    create_multiresolution_grid,
    get_hierarchical_cells,
)
from .parallel import (
    ParallelConfig,
    ParallelGridEngine,
    create_data_stream,
    create_file_stream,
    parallel_intersect,
    stream_grid_processing,
)
from .pluscode import PlusCodeGrid
from .quadkey import QuadkeyGrid
from .relationships import (
    GridRelationshipAnalyzer,
    RelationshipType,
    analyze_coverage,
    analyze_relationship,
    create_adjacency_matrix,
    create_relationship_matrix,
    find_adjacent_cells,
    find_cell_clusters,
    find_contained_cells,
    find_overlapping_cells,
    is_adjacent,
)
from .rhealpix import RHEALPixGrid
from .s2 import S2Grid
from .slippy import SlippyGrid

# Grid system singletons for direct access.
# Default precision and valid range come from each grid class (DEFAULT_PRECISION
# / MIN_PRECISION / MAX_PRECISION), so the wrapper needs no per-grid config here.
A5 = GridWrapper(A5Grid)
Geohash = GridWrapper(GeohashGrid)
MGRS = GridWrapper(MGRSGrid)
H3 = GridWrapper(H3Grid)
S2 = GridWrapper(S2Grid)
Quadkey = GridWrapper(QuadkeyGrid)
Slippy = GridWrapper(SlippyGrid)
CSquares = GridWrapper(CSquaresGrid)
GARS = GridWrapper(GARSGrid)
Maidenhead = GridWrapper(MaidenheadGrid)
PlusCode = GridWrapper(PlusCodeGrid)
EAQuad = GridWrapper(EAQuadGrid)
RHEALPix = GridWrapper(RHEALPixGrid)

# Registry mapping canonical names to grid singletons, for dynamic access.
_GRID_REGISTRY: dict[str, GridWrapper] = {
    "a5": A5,
    "geohash": Geohash,
    "mgrs": MGRS,
    "h3": H3,
    "s2": S2,
    "quadkey": Quadkey,
    "slippy": Slippy,
    "csquares": CSquares,
    "gars": GARS,
    "maidenhead": Maidenhead,
    "pluscode": PlusCode,
    "eaquad": EAQuad,
    "rhealpix": RHEALPix,
}


def grids() -> list[str]:
    """Sorted names of the available grid systems (for use with :func:`grid`)."""
    return sorted(_GRID_REGISTRY)


def grid(name: str, precision: int | None = None) -> GridWrapper:
    """
    Look up a grid system by name.

    Enables dynamic / config-driven access without importing each singleton::

        g = m3s.grid("h3", precision=7)
        cells = g.from_geometry(polygon)

    Parameters
    ----------
    name : str
        Grid system name (case-insensitive), e.g. ``"h3"``. See :func:`grids`.
    precision : int, optional
        If given, return a wrapper bound to this precision.

    Returns
    -------
    GridWrapper
        The grid singleton (or a precision-bound copy when ``precision`` is set).

    Raises
    ------
    ValueError
        If ``name`` is not a known grid system.
    """
    try:
        wrapper = _GRID_REGISTRY[name.lower()]
    except KeyError:
        valid = ", ".join(grids())
        raise ValueError(
            f"Unknown grid system {name!r}. Valid systems: {valid}"
        ) from None
    return wrapper.with_precision(precision) if precision is not None else wrapper


__version__ = "0.5.2"
__all__ = [
    # Grid singletons
    "A5",
    "Geohash",
    "MGRS",
    "H3",
    "S2",
    "Quadkey",
    "Slippy",
    "CSquares",
    "GARS",
    "Maidenhead",
    "PlusCode",
    "EAQuad",
    "RHEALPix",
    # Dynamic grid access
    "grid",
    "grids",
    # Core grid systems (for advanced use)
    "BaseGrid",
    "A5Grid",
    "GeohashGrid",
    "MGRSGrid",
    "H3Grid",
    "CSquaresGrid",
    "GARSGrid",
    "MaidenheadGrid",
    "PlusCodeGrid",
    "QuadkeyGrid",
    "S2Grid",
    "SlippyGrid",
    "EAQuadGrid",
    "RHEALPixGrid",
    # Modern API
    "GridBuilder",
    "GridWrapper",
    "GridCellCollection",
    "PrecisionFinder",
    "PrecisionSelector",
    "PrecisionRecommendation",
    "AreaCalculator",
    "PerformanceProfiler",
    "GridQueryResult",
    "MultiGridComparator",
    # Parallel processing
    "ParallelConfig",
    "ParallelGridEngine",
    "parallel_intersect",
    "stream_grid_processing",
    "create_data_stream",
    "create_file_stream",
    # Memory management
    "MemoryMonitor",
    "LazyGeodataFrame",
    "StreamingGridProcessor",
    "optimize_geodataframe_memory",
    "estimate_memory_usage",
    # Grid conversion utilities
    "GridConverter",
    "convert_cell",
    "convert_cells",
    "get_equivalent_precision",
    "create_conversion_table",
    "list_grid_systems",
    # Relationship analysis
    "GridRelationshipAnalyzer",
    "RelationshipType",
    "analyze_relationship",
    "is_adjacent",
    "find_contained_cells",
    "find_overlapping_cells",
    "find_adjacent_cells",
    "create_relationship_matrix",
    "create_adjacency_matrix",
    "find_cell_clusters",
    "analyze_coverage",
    # Multi-resolution operations
    "MultiResolutionGrid",
    "ResolutionLevel",
    "create_multiresolution_grid",
    "get_hierarchical_cells",
    "create_adaptive_grid",
]
