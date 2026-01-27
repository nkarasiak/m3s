import pytest
from shapely.geometry import Polygon

from m3s import CSquaresGrid


def test_csquares_cell_and_bbox():
    grid = CSquaresGrid(precision=3)
    cell = grid.cell(40.7128, -74.0060)
    assert cell.precision == 3
    assert isinstance(cell.polygon, Polygon)

    bbox = (-74.2, 40.6, -73.8, 40.9)
    cells = grid.cells_in_bbox(bbox)
    assert cells
