import pytest
from shapely.geometry import Polygon

from m3s import GeohashGrid


def test_geohash_cell_and_from_id():
    grid = GeohashGrid(precision=5)
    cell = grid.cell(40.7128, -74.0060)
    assert cell.precision == 5
    assert len(str(cell.id)) == 5
    assert isinstance(cell.polygon, Polygon)

    same = grid.from_id(cell.id)
    assert same.id == cell.id


def test_geohash_neighbors_and_bbox():
    grid = GeohashGrid(precision=4)
    cell = grid.cell(40.7128, -74.0060)
    neighbors = grid.neighbors(cell)
    assert neighbors
    assert all(n.id != cell.id for n in neighbors)

    bbox = (-74.1, 40.7, -74.0, 40.8)
    cells = grid.cells_in_bbox(bbox)
    assert cells
