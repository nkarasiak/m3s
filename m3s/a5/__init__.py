"""
A5 Pentagonal Grid System.

This module implements the A5 pentagonal DGGS (Discrete Global Grid System)
based on dodecahedral projection, compatible with Felix Palmer's A5 specification.

Public API
----------
The following functions and classes match Felix Palmer's A5 API:

Functions:
    lonlat_to_cell(lon, lat, resolution) -> int
    cell_to_lonlat(cell_id) -> Tuple[float, float]
    cell_to_boundary(cell_id) -> List[Tuple[float, float]]
    get_parent(cell_id) -> int
    get_children(cell_id) -> List[int]
    get_resolution(cell_id) -> int

Classes:
    A5Grid: M3S integration for A5 grid system
"""

from m3s.a5.cell import (
    cell_to_boundary,
    cell_to_lonlat,
    get_children,
    get_parent,
    get_resolution,
    lonlat_to_cell,
)
from m3s.a5.grid import A5Grid

__all__ = [
    "A5Grid",
    "lonlat_to_cell",
    "cell_to_lonlat",
    "cell_to_boundary",
    "get_parent",
    "get_children",
    "get_resolution",
]
