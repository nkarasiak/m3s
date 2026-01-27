import pytest
from shapely.geometry import Polygon

from m3s import S2Grid


def test_s2_cell_and_from_id():
    grid = S2Grid(precision=10)
    cell = grid.cell(40.7128, -74.0060)
    assert cell.precision == 10
    assert isinstance(cell.polygon, Polygon)

    same = grid.from_id(cell.id)
    assert same.id == cell.id


def test_s2_neighbors_and_bbox():
    grid = S2Grid(precision=10)
    cell = grid.cell(40.7128, -74.0060)
    neighbors = grid.neighbors(cell)
    assert neighbors

    bbox = (-74.2, 40.6, -73.8, 40.9)
    cells = grid.cells_in_bbox(bbox)
    assert cells

