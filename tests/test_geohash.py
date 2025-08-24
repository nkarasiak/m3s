"""
Tests for GeohashGrid implementation.
"""

import pytest
from shapely.geometry import Polygon

from m3s import GeohashGrid


class TestGeohashGrid:
    def test_grid_initialization(self):
        grid = GeohashGrid(precision=5)
        assert grid.precision == 5

    def test_invalid_precision(self):
        with pytest.raises(ValueError):
            GeohashGrid(precision=0)
        with pytest.raises(ValueError):
            GeohashGrid(precision=13)

    def test_get_cell_from_point(self):
        grid = GeohashGrid(precision=5)
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        assert cell is not None
        assert len(cell.identifier) == 5
        assert cell.precision == 5
        assert isinstance(cell.polygon, Polygon)

    def test_get_cell_from_identifier(self):
        grid = GeohashGrid(precision=5)
        cell = grid.get_cell_from_identifier("dr5ru")

        assert cell.identifier == "dr5ru"
        assert cell.precision == 5
        assert isinstance(cell.polygon, Polygon)

    def test_polygon_intersection(self):
        grid = GeohashGrid(precision=3)

        test_polygon = Polygon(
            [(-74.1, 40.7), (-74.0, 40.7), (-74.0, 40.8), (-74.1, 40.8), (-74.1, 40.7)]
        )

        bounds = test_polygon.bounds
        min_lon, min_lat, max_lon, max_lat = bounds
        candidate_cells = grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)
        intersecting_cells = [
            cell for cell in candidate_cells if cell.polygon.intersects(test_polygon)
        ]

        assert len(intersecting_cells) > 0
        for cell in intersecting_cells:
            assert isinstance(cell.polygon, Polygon)
            assert cell.polygon.intersects(test_polygon)

    def test_get_neighbors(self):
        grid = GeohashGrid(precision=3)
        cell = grid.get_cell_from_point(40.7128, -74.0060)
        neighbors = grid.get_neighbors(cell)

        assert len(neighbors) > 0
        for neighbor in neighbors:
            assert neighbor.identifier != cell.identifier

    def test_expand_cell(self):
        grid = GeohashGrid(precision=3)
        cell = grid.get_cell_from_identifier("dr5")
        expanded = grid.expand_cell(cell)

        assert len(expanded) == 32
        for expanded_cell in expanded:
            assert expanded_cell.identifier.startswith(cell.identifier)
            assert len(expanded_cell.identifier) == len(cell.identifier) + 1
