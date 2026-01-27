"""M3S - Multi Spatial Subdivision System."""

from .core import (
    Cell,
    GridBase,
    GridProtocol,
    InvalidLatitude,
    InvalidLongitude,
    InvalidPrecision,
    M3SError,
)
from .grids import (
    A5Grid,
    CSquaresGrid,
    GARSGrid,
    GeohashGrid,
    H3Grid,
    MaidenheadGrid,
    MGRSGrid,
    PlusCodeGrid,
    QuadkeyGrid,
    S2Grid,
    SlippyGrid,
    What3WordsGrid,
)
from .conversion import (
    convert_cell,
    convert_cells,
    create_conversion_table,
    get_equivalent_precision,
    list_grid_systems,
)
from .relationships import (
    analyze_relationship,
    create_adjacency_matrix,
    find_adjacent_cells,
)
from .multiresolution import create_adaptive_grid, create_multiresolution_grid
from .ops.intersects import intersects
from .api import grid
from . import precision
from . import systems

__version__ = "0.6.0"

__all__ = [
    "Cell",
    "GridBase",
    "GridProtocol",
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
    "What3WordsGrid",
    "intersects",
    "convert_cell",
    "convert_cells",
    "create_conversion_table",
    "get_equivalent_precision",
    "list_grid_systems",
    "analyze_relationship",
    "create_adjacency_matrix",
    "find_adjacent_cells",
    "create_multiresolution_grid",
    "create_adaptive_grid",
    "M3SError",
    "InvalidPrecision",
    "InvalidLatitude",
    "InvalidLongitude",
    "grid",
    "precision",
    "systems",
]
