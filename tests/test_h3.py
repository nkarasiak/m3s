import pytest
from shapely.geometry import Polygon

from m3s import H3Grid


def test_h3_cell_and_from_id():
    grid = H3Grid(precision=5)
    cell = grid.cell(40.7128, -74.0060)
    assert cell.precision == 5
    assert isinstance(cell.polygon, Polygon)

    same = grid.from_id(cell.id)
    assert same.id == cell.id


def test_h3_neighbors_and_bbox():
    grid = H3Grid(precision=5)
    cell = grid.cell(40.7128, -74.0060)
    neighbors = grid.neighbors(cell)
    assert len(neighbors) == 6

    bbox = (-74.1, 40.7, -74.0, 40.8)
    cells = grid.cells_in_bbox(bbox)
    assert cells


def test_h3_bbox_overlap_density():
    grid = H3Grid(precision=6)
    bbox = (2.25, 48.82, 2.42, 48.90)
    cells = grid.cells_in_bbox(bbox)
    assert len(cells) >= 6

