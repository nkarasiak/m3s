"""
Completeness tests for regular lon/lat bbox enumeration.

GARS, Maidenhead, and CSquares route ``get_cells_in_bbox`` through
``BaseGrid._cells_in_bbox_regular``. These tests verify the enumerated set
matches a dense-sampling brute-force reference, so no boundary cell is missed
and no spurious cell is added.
"""

import pytest
from shapely.geometry import box

from m3s import CSquaresGrid, GARSGrid, MaidenheadGrid


def _brute_force_bbox(grid, min_lat, min_lon, max_lat, max_lon, lat_step, lon_step):
    """Return every cell hit by dense sampling that intersects the bbox.

    Samples far denser than the cell size over a region extended by one cell on
    every side, so any cell overlapping the bbox is guaranteed at least one
    interior sample point.
    """
    target = box(min_lon, min_lat, max_lon, max_lat)
    sub = 5
    found: dict[str, object] = {}
    lat = min_lat - lat_step
    while lat <= max_lat + lat_step + 1e-9:
        lon = min_lon - lon_step
        while lon <= max_lon + lon_step + 1e-9:
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                try:
                    cell = grid.get_cell_from_point(lat, lon)
                    if cell.polygon.intersects(target):
                        found[cell.identifier] = cell
                except Exception:
                    pass
            lon += lon_step / sub
        lat += lat_step / sub
    return set(found)


# (grid, precision, lat_step, lon_step, bbox) — bbox bounds offset from lattice
# lines to avoid measure-zero edge-touch ambiguity.
CASES = [
    (GARSGrid, 1, 0.5, 0.5, (40.13, -74.27, 40.91, -73.61)),
    (MaidenheadGrid, 2, 1.0, 2.0, (40.13, -74.27, 42.41, -71.61)),
    (CSquaresGrid, 3, 1.0, 1.0, (40.13, -74.27, 43.41, -70.61)),
]


@pytest.mark.parametrize("grid_cls,precision,lat_step,lon_step,bbox", CASES)
def test_bbox_enumeration_matches_reference(
    grid_cls, precision, lat_step, lon_step, bbox
):
    """Enumerated cell set equals the brute-force reference (no misses/extras)."""
    grid = grid_cls(precision=precision)
    min_lat, min_lon, max_lat, max_lon = bbox

    enumerated = {
        c.identifier for c in grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)
    }
    reference = _brute_force_bbox(
        grid, min_lat, min_lon, max_lat, max_lon, lat_step, lon_step
    )

    assert enumerated == reference


@pytest.mark.parametrize("grid_cls,precision,lat_step,lon_step,bbox", CASES)
def test_bbox_cells_intersect_box(grid_cls, precision, lat_step, lon_step, bbox):
    """Every returned cell actually intersects the requested bbox."""
    grid = grid_cls(precision=precision)
    min_lat, min_lon, max_lat, max_lon = bbox
    target = box(min_lon, min_lat, max_lon, max_lat)

    cells = grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)
    assert cells
    assert all(c.polygon.intersects(target) for c in cells)
