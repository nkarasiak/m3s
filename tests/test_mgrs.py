import pytest
from shapely.geometry import Polygon

from m3s import MGRSGrid


def test_mgrs_cell_and_from_id():
    grid = MGRSGrid(precision=2)
    cell = grid.cell(40.7128, -74.0060)
    assert cell.precision == 2
    assert isinstance(cell.polygon, Polygon)

    same = grid.from_id(cell.id)
    assert same.id == cell.id


def test_mgrs_neighbors_and_bbox():
    grid = MGRSGrid(precision=1)
    cell = grid.cell(40.7128, -74.0060)
    neighbors = grid.neighbors(cell)
    assert neighbors

    bbox = (-74.2, 40.6, -73.8, 40.9)
    cells = grid.cells_in_bbox(bbox)
    assert cells
