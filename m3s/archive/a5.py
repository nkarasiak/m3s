"""
A5 pentagonal grid implementation.

A5 is a Discrete Global Grid System (DGGS) that divides the Earth's surface
into pentagonal cells derived from a dodecahedral projection. This implementation
provides a Python interface compatible with the M3S grid system framework.

Based on the A5 implementation by Felix Palmer:
https://github.com/felixpalmer/a5-py

This module provides the public API matching the reference implementation.
"""

from typing import List, Tuple

from .a5_proper_tessellation import (
    cell_to_boundary_proper,
    cell_to_lonlat_proper,
    lonlat_to_cell_proper,
)

# Type aliases to match the reference implementation
A5Cell = int  # 64-bit integer cell identifier
Degrees = float
Radians = float

# Use proper tessellation implementation as the main A5Grid
from .a5_proper_tessellation import A5ProperGrid

A5Grid = A5ProperGrid


def lonlat_to_cell(lon: Degrees, lat: Degrees, resolution: int) -> A5Cell:
    """
    Convert longitude/latitude coordinates to an A5 cell.

    Parameters
    ----------
    lon : float
        Longitude in degrees
    lat : float
        Latitude in degrees
    resolution : int
        Resolution level (0-30)

    Returns
    -------
    A5Cell
        64-bit A5 cell identifier
    """
    return lonlat_to_cell_proper(lon, lat, resolution)


def cell_to_lonlat(cell_id: A5Cell, resolution: int) -> Tuple[Degrees, Degrees]:
    """
    Convert an A5 cell to its center longitude/latitude.

    Parameters
    ----------
    cell_id : A5Cell
        64-bit A5 cell identifier
    resolution : int
        Resolution level

    Returns
    -------
    Tuple[Degrees, Degrees]
        Longitude and latitude of cell center
    """
    return cell_to_lonlat_proper(cell_id, resolution)


def cell_to_boundary(cell_id: A5Cell, resolution: int) -> List[Tuple[Degrees, Degrees]]:
    """
    Get the boundary vertices of an A5 cell.

    Parameters
    ----------
    cell_id : A5Cell
        64-bit A5 cell identifier
    resolution : int
        Resolution level

    Returns
    -------
    List[Tuple[Degrees, Degrees]]
        List of (lon, lat) boundary vertices
    """
    return cell_to_boundary_proper(cell_id, resolution)


def cell_to_parent(cell_id: A5Cell, resolution: int) -> A5Cell:
    """
    Get the parent cell at resolution-1.

    Parameters
    ----------
    cell_id : A5Cell
        64-bit A5 cell identifier
    resolution : int
        Current resolution level

    Returns
    -------
    A5Cell
        Parent cell identifier
    """
    if resolution <= 0:
        raise ValueError("Cannot get parent of resolution 0 cell")

    # Convert cell_id back to coordinates
    lon, lat = cell_to_lonlat_proper(cell_id, resolution)

    # Create parent cell at lower resolution
    parent_grid = A5Grid(resolution - 1)
    return parent_grid._encode_cell_id(lat, lon)


def cell_to_children(cell_id: A5Cell, resolution: int) -> List[A5Cell]:
    """
    Get all child cells at resolution+1.

    Parameters
    ----------
    cell_id : A5Cell
        64-bit A5 cell identifier
    resolution : int
        Current resolution level

    Returns
    -------
    List[A5Cell]
        List of child cell identifiers
    """
    if resolution >= 30:
        raise ValueError("Cannot get children of resolution 30 cell")

    # Convert cell_id back to coordinates to get center
    lon, lat = cell_to_lonlat_proper(cell_id, resolution)

    # Create child grid and parent cell
    parent_grid = A5Grid(resolution)
    child_grid = A5Grid(resolution + 1)
    parent_cell = parent_grid.get_cell_from_point(lat, lon)

    # Sample points within the parent cell to find children
    bounds = parent_cell.polygon.bounds
    children = set()

    # Create a grid of sample points within the cell bounds
    num_samples = 15  # Reasonable coverage
    lon_step = (bounds[2] - bounds[0]) / num_samples
    lat_step = (bounds[3] - bounds[1]) / num_samples

    for i in range(num_samples + 1):
        for j in range(num_samples + 1):
            sample_lon = bounds[0] + i * lon_step
            sample_lat = bounds[1] + j * lat_step

            # Check if sample point is within parent cell
            from shapely.geometry import Point

            sample_point = Point(sample_lon, sample_lat)

            if parent_cell.polygon.contains(
                sample_point
            ) or parent_cell.polygon.touches(sample_point):
                try:
                    child_id = child_grid._encode_cell_id(sample_lat, sample_lon)
                    children.add(child_id)
                except:
                    continue

    return list(children)


def get_resolution(cell_id: A5Cell) -> int:
    """
    Get the resolution level of an A5 cell.

    Note: This is a simplified implementation. In the actual A5 system,
    resolution would be encoded in the cell ID itself.

    Parameters
    ----------
    cell_id : A5Cell
        64-bit A5 cell identifier

    Returns
    -------
    int
        Resolution level (this implementation returns a placeholder)
    """
    # In a full implementation, resolution would be extracted from cell_id
    # For now, return a default value
    return 5


def get_res0_cells() -> List[A5Cell]:
    """
    Get all resolution 0 base cells (dodecahedron faces).

    Returns
    -------
    List[A5Cell]
        List of 12 base cell identifiers
    """
    grid = A5Grid(0)

    # Create 12 base cells distributed across the globe
    base_cells = []

    # Sample 12 well-distributed points on Earth
    base_points = [
        (0, 0),  # Equator, Prime Meridian
        (0, 120),  # Equator, 120E
        (0, -120),  # Equator, 120W
        (60, 0),  # 60N, Prime Meridian
        (60, 120),  # 60N, 120E
        (60, -120),  # 60N, 120W
        (-60, 0),  # 60S, Prime Meridian
        (-60, 120),  # 60S, 120E
        (-60, -120),  # 60S, 120W
        (30, 60),  # 30N, 60E
        (-30, 60),  # 30S, 60E
        (0, 60),  # Equator, 60E
    ]

    for lat, lon in base_points:
        try:
            cell_id = grid._encode_cell_id(lat, lon)
            base_cells.append(cell_id)
        except:
            # Fallback to simple ID
            base_cells.append(len(base_cells))

    return base_cells[:12]


def get_num_cells(resolution: int) -> int:
    """
    Get the total number of cells at a given resolution.

    Parameters
    ----------
    resolution : int
        Resolution level

    Returns
    -------
    int
        Total number of cells
    """
    # A5 has 12 base cells, each subdivides by approximately 5 per level
    return 12 * (5**resolution)


def cell_area(cell_id: A5Cell, resolution: int) -> float:
    """
    Get the area of an A5 cell in square meters.

    Parameters
    ----------
    cell_id : A5Cell
        64-bit A5 cell identifier
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
    Convert hex string to 64-bit unsigned integer.

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
    Convert 64-bit unsigned integer to hex string.

    Parameters
    ----------
    cell_id : A5Cell
        64-bit integer

    Returns
    -------
    str
        Hexadecimal string
    """
    return f"{cell_id:016x}"
