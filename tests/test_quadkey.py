import pytest
from shapely.geometry import Polygon

from m3s import QuadkeyGrid


def test_quadkey_cell_and_from_id():
    grid = QuadkeyGrid(precision=12)
    cell = grid.cell(40.7128, -74.0060)
    assert cell.precision == 12
    assert isinstance(cell.polygon, Polygon)

    same = grid.from_id(cell.id)
    assert same.id == cell.id


def test_quadkey_neighbors_and_bbox():
    grid = QuadkeyGrid(precision=12)
    cell = grid.cell(40.7128, -74.0060)
    neighbors = grid.neighbors(cell)
    assert neighbors

    bbox = (-74.2, 40.6, -73.8, 40.9)
    cells = grid.cells_in_bbox(bbox)
    assert cells

