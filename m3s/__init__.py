"""
M3S - Multi Spatial Subdivision System.

A unified Python package for working with hierarchical spatial grid systems,
including grid conversion utilities, relationship analysis, and multi-resolution operations.
"""

# A5 Grid System
from .a5 import (
    A5Cell,
    A5Grid,
    cell_area,
    cell_to_boundary,
    cell_to_children,
    cell_to_lonlat,
    cell_to_parent,
    get_num_cells,
    get_res0_cells,
    get_resolution,
    hex_to_u64,
    lonlat_to_cell,
    u64_to_hex,
)

# Modern API
from .api import (
    AreaCalculator,
    GridBuilder,
    GridQueryResult,
    MultiGridComparator,
    PerformanceProfiler,
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
from .s2 import S2Grid
from .slippy import SlippyGrid
from .what3words import What3WordsGrid

__version__ = "0.5.1"
__all__ = [
    # Core grid systems
    "BaseGrid",
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
    "What3WordsGrid",
    "A5Grid",
    # Modern API
    "GridBuilder",
    "PrecisionSelector",
    "PrecisionRecommendation",
    "AreaCalculator",
    "PerformanceProfiler",
    "GridQueryResult",
    "MultiGridComparator",
    # A5 API functions
    "A5Cell",
    "lonlat_to_cell",
    "cell_to_lonlat",
    "cell_to_boundary",
    "cell_to_parent",
    "cell_to_children",
    "get_resolution",
    "get_res0_cells",
    "get_num_cells",
    "cell_area",
    "hex_to_u64",
    "u64_to_hex",
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
