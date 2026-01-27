import pytest
from shapely.geometry import Polygon

from m3s import What3WordsGrid


def test_what3words_cell_and_bbox():
    grid = What3WordsGrid(precision=1)
    cell = grid.cell(40.7128, -74.0060)
    assert cell.precision == 1
    assert isinstance(cell.polygon, Polygon)

    bbox = (-74.007, 40.712, -74.005, 40.713)
    cells = grid.cells_in_bbox(bbox)
    assert cells


def test_what3words_from_id_not_supported():
    grid = What3WordsGrid(precision=1)
    with pytest.raises(ValueError):
        grid.from_id("w3w.fake.code")
