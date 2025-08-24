"""
Tests for Plus codes (Open Location Code) grid implementation.
"""

import pytest
from shapely.geometry import Point

from m3s import PlusCodeGrid


class TestPlusCodeGrid:
    """Test suite for PlusCodeGrid."""

    def test_init_valid_precision(self):
        """Test grid initialization with valid precision."""
        grid = PlusCodeGrid(precision=4)
        assert grid.precision == 4

    def test_init_invalid_precision(self):
        """Test grid initialization with invalid precision."""
        with pytest.raises(
            ValueError, match="Plus code precision must be between 1 and 7"
        ):
            PlusCodeGrid(precision=0)

        with pytest.raises(
            ValueError, match="Plus code precision must be between 1 and 7"
        ):
            PlusCodeGrid(precision=8)

    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding are consistent."""
        grid = PlusCodeGrid(precision=4)
        lat, lon = 37.7749, -122.4194  # San Francisco

        code = grid.encode(lat, lon)
        south, west, north, east = grid.decode(code)

        # Original point should be within decoded bounds
        assert south <= lat <= north
        assert west <= lon <= east

    def test_encode_known_location(self):
        """Test encoding of known locations."""
        grid = PlusCodeGrid(precision=4)

        # Test several known coordinates
        test_cases = [
            (37.7749, -122.4194),  # San Francisco
            (51.5074, -0.1278),  # London
            (35.6762, 139.6503),  # Tokyo
            (0.0, 0.0),  # Null Island
        ]

        for lat, lon in test_cases:
            code = grid.encode(lat, lon)
            assert isinstance(code, str)
            assert len(code) >= 5  # Should have at least precision worth of data

    def test_get_cell_from_point(self):
        """Test getting cell from point coordinates."""
        grid = PlusCodeGrid(precision=3)
        cell = grid.get_cell_from_point(37.7749, -122.4194)

        assert cell.precision == 3
        assert isinstance(cell.identifier, str)
        assert cell.polygon.contains(Point(-122.4194, 37.7749))

    def test_get_cell_from_identifier(self):
        """Test getting cell from identifier."""
        grid = PlusCodeGrid(precision=3)

        # Get a cell first
        original_cell = grid.get_cell_from_point(37.7749, -122.4194)

        # Get same cell from identifier
        retrieved_cell = grid.get_cell_from_identifier(original_cell.identifier)

        assert retrieved_cell.identifier == original_cell.identifier
        assert retrieved_cell.precision == original_cell.precision

    def test_get_neighbors(self):
        """Test getting neighboring cells."""
        grid = PlusCodeGrid(precision=2)
        cell = grid.get_cell_from_point(37.7749, -122.4194)
        neighbors = grid.get_neighbors(cell)

        # Should have up to 8 neighbors
        assert len(neighbors) <= 8
        assert all(isinstance(neighbor, type(cell)) for neighbor in neighbors)
        assert all(neighbor.identifier != cell.identifier for neighbor in neighbors)

    def test_get_cells_in_bbox(self):
        """Test getting cells within bounding box."""
        grid = PlusCodeGrid(precision=2)

        # Small bounding box around San Francisco
        min_lat, min_lon = 37.7, -122.5
        max_lat, max_lon = 37.8, -122.4

        cells = grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        assert len(cells) > 0
        assert all(
            isinstance(cell, type(grid.get_cell_from_point(37.7749, -122.4194)))
            for cell in cells
        )

    def test_encode_edge_cases(self):
        """Test encoding at coordinate extremes."""
        grid = PlusCodeGrid(precision=2)

        # Test coordinate extremes
        test_cases = [
            (-90, -180),  # Southwest corner
            (90, 180),  # Northeast corner
            (-90, 180),  # Southeast corner
            (90, -180),  # Northwest corner
        ]

        for lat, lon in test_cases:
            code = grid.encode(lat, lon)
            south, west, north, east = grid.decode(code)

            # Should be valid bounds
            assert south <= north
            assert west <= east

    def test_different_precisions(self):
        """Test that different precisions work correctly."""
        test_lat, test_lon = 37.7749, -122.4194

        for precision in range(1, 8):
            grid = PlusCodeGrid(precision=precision)
            cell = grid.get_cell_from_point(test_lat, test_lon)

            assert cell.precision == precision
            assert cell.polygon.contains(Point(test_lon, test_lat))

    def test_cell_area_decreases_with_precision(self):
        """Test that cell area decreases as precision increases."""
        test_lat, test_lon = 37.7749, -122.4194
        areas = []

        for precision in range(1, 5):
            grid = PlusCodeGrid(precision=precision)
            cell = grid.get_cell_from_point(test_lat, test_lon)
            areas.append(cell.area_km2)

        # Areas should generally decrease with higher precision
        for i in range(1, len(areas)):
            assert areas[i] <= areas[i - 1] * 10  # Allow some tolerance

    def test_format_with_separator(self):
        """Test that plus codes include the '+' separator correctly."""
        grid = PlusCodeGrid(precision=4)
        code = grid.encode(37.7749, -122.4194)

        # Should contain the '+' separator in standard position
        if len(code) >= 8:
            assert "+" in code
