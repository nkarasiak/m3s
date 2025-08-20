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

__version__ = "0.1.0"
__all__ = ["BaseGrid", "GeohashGrid", "MGRSGrid", "H3Grid", "CSquaresGrid"]
