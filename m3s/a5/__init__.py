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
    cell_to_parent(cell_id, resolution) -> int
    cell_to_children(cell_id, resolution) -> List[int]
    get_res0_cells() -> List[int]
    get_num_cells(resolution) -> int
    cell_area(cell_id, resolution) -> float
    hex_to_u64(hex_string) -> int
    u64_to_hex(cell_id) -> str

Classes:
    A5Grid: M3S integration for A5 grid system

Types:
    A5Cell: Type alias for int (64-bit cell identifier)
"""

from typing import List, Optional, Tuple

from m3s.a5.cell import (
    cell_to_boundary as _cell_to_boundary_impl,
)
from m3s.a5.cell import (
    cell_to_lonlat as _cell_to_lonlat_impl,
)
from m3s.a5.cell import (
    get_children as _get_children_impl,
)
from m3s.a5.cell import (
    get_parent as _get_parent_impl,
)
from m3s.a5.cell import (
    get_resolution,
    lonlat_to_cell,
)
from m3s.a5.grid import A5Grid

# Type aliases
A5Cell = int  # 64-bit integer cell identifier


# Wrapper functions for API compatibility with optional resolution parameter
def cell_to_lonlat(
    cell_id: A5Cell, resolution: Optional[int] = None
) -> Tuple[float, float]:
    """
    Convert A5 cell ID to center coordinates.

    Parameters
    ----------
    cell_id : A5Cell
        Cell identifier
    resolution : int, optional
        Resolution level (unused, resolution extracted from cell_id)

    Returns
    -------
    Tuple[float, float]
        (lon, lat) in degrees
    """
    return _cell_to_lonlat_impl(cell_id)


def cell_to_boundary(
    cell_id: A5Cell, resolution: Optional[int] = None
) -> List[Tuple[float, float]]:
    """
    Get cell boundary vertices.

    Parameters
    ----------
    cell_id : A5Cell
        Cell identifier
    resolution : int, optional
        Resolution level (unused, resolution extracted from cell_id)

    Returns
    -------
    List[Tuple[float, float]]
        List of (lon, lat) boundary vertices
    """
    return _cell_to_boundary_impl(cell_id)


def get_parent(cell_id: A5Cell) -> A5Cell:
    """
    Get parent cell at resolution-1.

    Parameters
    ----------
    cell_id : A5Cell
        Child cell ID

    Returns
    -------
    A5Cell
        Parent cell ID
    """
    return _get_parent_impl(cell_id)


def get_children(cell_id: A5Cell) -> List[A5Cell]:
    """
    Get child cells at resolution+1.

    Parameters
    ----------
    cell_id : A5Cell
        Parent cell ID

    Returns
    -------
    List[A5Cell]
        List of child cell IDs
    """
    return _get_children_impl(cell_id)


# Alias functions for alternate API
def cell_to_parent(cell_id: A5Cell, resolution: Optional[int] = None) -> A5Cell:
    """
    Get parent cell at resolution-1 (alternate API).

    Parameters
    ----------
    cell_id : A5Cell
        Child cell ID
    resolution : int, optional
        Current resolution (unused, kept for API compatibility)

    Returns
    -------
    A5Cell
        Parent cell ID
    """
    return _get_parent_impl(cell_id)


def cell_to_children(cell_id: A5Cell, resolution: Optional[int] = None) -> List[A5Cell]:
    """
    Get child cells at resolution+1 (alternate API).

    Parameters
    ----------
    cell_id : A5Cell
        Parent cell ID
    resolution : int, optional
        Current resolution (unused, kept for API compatibility)

    Returns
    -------
    List[A5Cell]
        List of child cell IDs
    """
    return _get_children_impl(cell_id)


def get_res0_cells() -> List[A5Cell]:
    """
    Get all resolution 0 base cells (12 dodecahedron faces).

    Returns
    -------
    List[A5Cell]
        List of 12 base cell identifiers
    """
    # Sample many points across globe to ensure we hit all 12 dodecahedron faces
    # Using a systematic grid sampling approach
    base_cells = []
    seen_cells = set()

    # Sample points in a grid pattern across latitudes and longitudes
    for lat in range(-80, 90, 40):  # -80, -40, 0, 40, 80
        for lon in range(-180, 180, 60):  # -180, -120, -60, 0, 60, 120
            try:
                cell_id = lonlat_to_cell(lon, lat, 0)
                if cell_id not in seen_cells:
                    base_cells.append(cell_id)
                    seen_cells.add(cell_id)
                    if len(base_cells) >= 12:
                        return base_cells
            except:
                pass

    # If we still don't have 12, add poles
    if len(base_cells) < 12:
        for pole_lat in [89, -89]:
            for pole_lon in range(0, 360, 90):
                try:
                    cell_id = lonlat_to_cell(pole_lon, pole_lat, 0)
                    if cell_id not in seen_cells:
                        base_cells.append(cell_id)
                        seen_cells.add(cell_id)
                        if len(base_cells) >= 12:
                            return base_cells
                except:
                    pass

    return base_cells


def get_num_cells(resolution: int) -> int:
    """
    Get total number of cells at a resolution.

    Parameters
    ----------
    resolution : int
        Resolution level

    Returns
    -------
    int
        Total number of cells (12 * 5^resolution)
    """
    return 12 * (5**resolution)  # type: ignore[no-any-return]


def cell_area(cell_id: A5Cell, resolution: int) -> float:
    """
    Get cell area in square meters.

    Parameters
    ----------
    cell_id : A5Cell
        Cell identifier
    resolution : int
        Resolution level

    Returns
    -------
    float
        Area in square meters
    """
    grid = A5Grid(resolution)
    return grid.area_km2 * 1_000_000  # Convert km² to m²


def hex_to_u64(hex_string: str) -> A5Cell:
    """
    Convert hex string to 64-bit integer.

    Parameters
    ----------
    hex_string : str
        Hexadecimal string

    Returns
    -------
    A5Cell
        64-bit integer
    """
    return int(hex_string, 16)


def u64_to_hex(cell_id: A5Cell) -> str:
    """
    Convert 64-bit integer to hex string.

    Parameters
    ----------
    cell_id : A5Cell
        64-bit integer

    Returns
    -------
    str
        Hexadecimal string (16 characters, zero-padded)
    """
    return f"{cell_id:016x}"


__all__ = [
    "A5Grid",
    "A5Cell",
    "lonlat_to_cell",
    "cell_to_lonlat",
    "cell_to_boundary",
    "get_parent",
    "get_children",
    "cell_to_parent",
    "cell_to_children",
    "get_resolution",
    "get_res0_cells",
    "get_num_cells",
    "cell_area",
    "hex_to_u64",
    "u64_to_hex",
]
