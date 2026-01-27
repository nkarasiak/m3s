import pytest
from shapely.geometry import Polygon

from m3s import PlusCodeGrid


def test_pluscode_cell_and_bbox():
    grid = PlusCodeGrid(precision=4)
    cell = grid.cell(40.7128, -74.0060)
    assert cell.precision == 4
    assert isinstance(cell.polygon, Polygon)

    bbox = (-74.007, 40.712, -74.005, 40.713)
    cells = grid.cells_in_bbox(bbox)
    assert cells
