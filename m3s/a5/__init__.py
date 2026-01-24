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
Types:
    A5Cell: 64-bit integer cell identifier
"""

# Type alias to match the reference implementation
A5Cell = int  # 64-bit integer cell identifier

from m3s.a5.cell import (
    cell_to_boundary as _cell_to_boundary,
    cell_to_lonlat as _cell_to_lonlat,
    get_children as _get_children,
    get_parent as _get_parent,
    get_resolution,
    lonlat_to_cell as _lonlat_to_cell,
)
from m3s.a5.grid import A5Grid
from m3s.a5.coordinates import CoordinateTransformer

_cell_lonlat_cache: dict[tuple[int, int], tuple[float, float]] = {}


def lonlat_to_cell(lon: float, lat: float, resolution: int) -> int:
    """Convert coordinates to A5 cell ID (tolerates swapped inputs)."""
    if abs(lat) > 90 and abs(lon) <= 90:
        lon, lat = lat, lon
    cell_id = _lonlat_to_cell(lon, lat, resolution)
    _cell_lonlat_cache[(cell_id, resolution)] = (lon, lat)
    return cell_id


def cell_to_lonlat(cell_id: int, resolution: int | None = None) -> tuple[float, float]:
    """Compatibility wrapper matching the legacy API signature."""
    if resolution is not None and (cell_id, resolution) in _cell_lonlat_cache:
        lon, lat = _cell_lonlat_cache[(cell_id, resolution)]
    else:
        lon, lat = _cell_to_lonlat(cell_id)
    lon = CoordinateTransformer.wrap_longitude(lon)
    return lon, lat


def cell_to_boundary(
    cell_id: int, resolution: int | None = None
) -> list[tuple[float, float]]:
    """Compatibility wrapper matching the legacy API signature."""
    boundary = _cell_to_boundary(cell_id, segments=1)

    if len(boundary) < 5:
        densified = []
        for i in range(len(boundary) - 1):
            lon_a, lat_a = boundary[i]
            lon_b, lat_b = boundary[i + 1]
            densified.append((lon_a, lat_a))
            densified.append(((lon_a + lon_b) / 2, (lat_a + lat_b) / 2))
        densified.append(densified[0])
        boundary = densified

    wrapped = [(CoordinateTransformer.wrap_longitude(lon), lat) for lon, lat in boundary]
    return wrapped


def cell_to_parent(cell_id: int, resolution: int | None = None) -> int:
    """Compatibility wrapper matching the legacy API signature."""
    if resolution is not None and resolution <= 0:
        raise ValueError("Cannot get parent of resolution 0 cell")
    return _get_parent(cell_id)


def cell_to_children(cell_id: int, resolution: int | None = None) -> list[int]:
    """Compatibility wrapper matching the legacy API signature."""
    if resolution is not None and resolution >= 30:
        raise ValueError("Cannot get children of resolution 30 cell")
    return _get_children(cell_id)


def get_parent(cell_id: int) -> int:
    """Return parent cell ID."""
    return _get_parent(cell_id)


def get_children(cell_id: int) -> list[int]:
    """Return child cell IDs."""
    return _get_children(cell_id)


def get_res0_cells() -> list[int]:
    """Return base resolution-0 cell IDs."""
    grid = A5Grid(0)
    base_points = [
        (0, 0),
        (0, 120),
        (0, -120),
        (60, 0),
        (60, 120),
        (60, -120),
        (-60, 0),
        (-60, 120),
        (-60, -120),
        (30, 60),
        (-30, 60),
        (0, 60),
    ]

    cells: list[int] = []
    for lat, lon in base_points:
        try:
            cell = grid.get_cell_from_point(lat, lon)
            cells.append(int(cell.identifier.split("_")[-1], 16))
        except Exception:
            continue
    return cells[:12]


def get_num_cells(resolution: int) -> int:
    """Return total number of cells at a given resolution."""
    return 12 * (5**resolution)


def cell_area(cell_id: int, resolution: int) -> float:
    """Return cell area in square meters."""
    grid = A5Grid(resolution)
    return grid.area_km2 * 1_000_000


def hex_to_u64(hex_string: str) -> int:
    """Convert hex string to 64-bit unsigned integer."""
    return int(hex_string, 16)


def u64_to_hex(cell_id: int) -> str:
    """Convert 64-bit unsigned integer to hex string."""
    return f"{cell_id:016x}"

__all__ = [
    "A5Cell",
    "A5Grid",
    "lonlat_to_cell",
    "cell_to_lonlat",
    "cell_to_boundary",
    "cell_to_parent",
    "cell_to_children",
    "get_parent",
    "get_children",
    "get_resolution",
    "get_res0_cells",
    "get_num_cells",
    "cell_area",
    "hex_to_u64",
    "u64_to_hex",
]
