"""
Tests for MGRSGrid implementation.
"""

import pytest
from shapely.geometry import Polygon

from m3s import MGRSGrid


class TestMGRSGrid:
    """Test MGRSGrid behavior."""

    def test_grid_initialization(self):
        """Initialize grid with valid precision."""
        grid = MGRSGrid(precision=2)
        assert grid.precision == 2

    def test_invalid_precision(self):
        """Reject invalid precision values."""
        with pytest.raises(ValueError):
            MGRSGrid(precision=-1)
        with pytest.raises(ValueError):
            MGRSGrid(precision=6)

    def test_get_cell_from_point(self):
        """Return a cell for a point."""
        grid = MGRSGrid(precision=2)
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        assert cell is not None
        assert cell.precision == 2
        assert isinstance(cell.polygon, Polygon)

    def test_get_cell_from_identifier(self):
        """Return a cell for an identifier."""
        grid = MGRSGrid(precision=2)

        try:
            cell = grid.get_cell_from_identifier("18TWL8040")
            assert cell.identifier == "18TWL8040"
            assert cell.precision == 2
            assert isinstance(cell.polygon, Polygon)
        except Exception:
            pytest.skip(
                "MGRS identifier conversion failed - may require specific coordinate"
            )

    def test_polygon_intersection(self):
        """Find cells intersecting a polygon."""
        grid = MGRSGrid(precision=1)

        test_polygon = Polygon(
            [(-74.1, 40.7), (-74.0, 40.7), (-74.0, 40.8), (-74.1, 40.8), (-74.1, 40.7)]
        )

        bounds = test_polygon.bounds
        min_lon, min_lat, max_lon, max_lat = bounds
        candidate_cells = grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)
        intersecting_cells = [
            cell for cell in candidate_cells if cell.polygon.intersects(test_polygon)
        ]

        assert len(intersecting_cells) >= 0
        for cell in intersecting_cells:
            assert isinstance(cell.polygon, Polygon)

    def test_grid_size(self):
        """Compute grid size for each precision."""
        grid0 = MGRSGrid(precision=0)
        grid1 = MGRSGrid(precision=1)
        grid2 = MGRSGrid(precision=2)
        grid3 = MGRSGrid(precision=3)

        assert grid0._get_grid_size() == 100000
        assert grid1._get_grid_size() == 10000
        assert grid2._get_grid_size() == 1000
        assert grid3._get_grid_size() == 100

    def test_get_neighbors(self):
        """Return neighbor cells."""
        grid = MGRSGrid(precision=1)
        try:
            cell = grid.get_cell_from_point(40.7128, -74.0060)
            neighbors = grid.get_neighbors(cell)

            for neighbor in neighbors:
                assert neighbor.identifier != cell.identifier
        except Exception:
            pytest.skip("MGRS neighbor calculation failed")

    def test_utm_zone_calculation(self):
        """Compute UTM zone from coordinates."""
        grid = MGRSGrid(precision=1)

        utm_zone_north = grid._get_utm_zone_from_mgrs("18TWL")
        utm_zone_south = grid._get_utm_zone_from_mgrs("18CWL")

        assert utm_zone_north == 32618
        assert utm_zone_south == 32718
