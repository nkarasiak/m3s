"""
Griddy - A Python package for creating and working with spatial grids.

This package provides functionality to work with various spatial grid systems
like Geohash, MGRS (Military Grid Reference System), H3, and C-squares.
"""

from .base import BaseGrid
from .csquares import CSquaresGrid
from .geohash import GeohashGrid
from .h3 import H3Grid
from .mgrs import MGRSGrid
from .parallel import (
    ParallelConfig,
    ParallelGridEngine,
    create_data_stream,
    create_file_stream,
    parallel_intersect,
    stream_grid_processing,
)
from .quadkey import QuadkeyGrid
from .s2 import S2Grid
from .slippy import SlippyGrid

__version__ = "0.3.0"
__all__ = [
    "BaseGrid",
    "GeohashGrid",
    "MGRSGrid",
    "H3Grid",
    "CSquaresGrid",
    "QuadkeyGrid",
    "S2Grid",
    "SlippyGrid",
    "ParallelConfig",
    "ParallelGridEngine",
    "parallel_intersect",
    "stream_grid_processing",
    "create_data_stream",
    "create_file_stream",
]
