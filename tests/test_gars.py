import pytest
from shapely.geometry import Polygon

from m3s import GARSGrid


def test_gars_cell_and_bbox():
    grid = GARSGrid(precision=2)
    cell = grid.cell(40.7128, -74.0060)
    assert cell.precision == 2
    assert isinstance(cell.polygon, Polygon)

    bbox = (-74.2, 40.6, -73.8, 40.9)
    cells = grid.cells_in_bbox(bbox)
    assert cells


def test_gars_precision3_cell_size_and_bbox():
    grid = GARSGrid(precision=3)
    cell = grid.cell(48.8566, 2.3522)
    min_lon, min_lat, max_lon, max_lat = cell.bbox
    assert pytest.approx(max_lon - min_lon, rel=0, abs=1e-6) == 1.0 / 12.0
    assert pytest.approx(max_lat - min_lat, rel=0, abs=1e-6) == 1.0 / 12.0

    bbox = (2.25, 48.82, 2.42, 48.90)
    cells = grid.cells_in_bbox(bbox)
    assert len(cells) == 6
