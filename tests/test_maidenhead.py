import pytest
from shapely.geometry import Polygon

from m3s import MaidenheadGrid


def test_maidenhead_cell_and_bbox():
    grid = MaidenheadGrid(precision=3)
    cell = grid.cell(40.7128, -74.0060)
    assert cell.precision == 3
    assert isinstance(cell.polygon, Polygon)

    bbox = (-74.2, 40.6, -73.8, 40.9)
    cells = grid.cells_in_bbox(bbox)
    assert cells


def test_maidenhead_precision3_bbox_density():
    grid = MaidenheadGrid(precision=3)
    bbox = (2.25, 48.82, 2.42, 48.90)
    cells = grid.cells_in_bbox(bbox)
    assert len(cells) >= 6
