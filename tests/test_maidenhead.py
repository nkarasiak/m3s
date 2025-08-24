"""
Tests for Maidenhead locator system grid implementation.
"""

import pytest
from shapely.geometry import Point

from m3s import MaidenheadGrid


class TestMaidenheadGrid:
    """Test suite for MaidenheadGrid."""

    def test_init_valid_precision(self):
        """Test grid initialization with valid precision."""
        grid = MaidenheadGrid(precision=3)
        assert grid.precision == 3

    def test_init_invalid_precision(self):
        """Test grid initialization with invalid precision."""
        with pytest.raises(
            ValueError, match="Maidenhead precision must be between 1 and 4"
        ):
            MaidenheadGrid(precision=0)

        with pytest.raises(
            ValueError, match="Maidenhead precision must be between 1 and 4"
        ):
            MaidenheadGrid(precision=5)

    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding are consistent."""
        grid = MaidenheadGrid(precision=3)
        lat, lon = 47.6062, -122.3321  # Seattle

        locator = grid.encode(lat, lon)
        south, west, north, east = grid.decode(locator)

        # Original point should be within decoded bounds
        assert south <= lat <= north
        assert west <= lon <= east

    def test_encode_known_locations(self):
        """Test encoding of known locations."""
        grid = MaidenheadGrid(precision=2)

        # Known test cases with expected results
        test_cases = [
            (37.7749, -122.4194, "CM87"),  # San Francisco
            (51.5074, -0.1278, "IO91"),  # London
            (35.6762, 139.6503, "PM95"),  # Tokyo
        ]

        for lat, lon, expected in test_cases:
            locator = grid.encode(lat, lon)
            assert locator.startswith(expected[:2])  # Field should match

    def test_encode_input_validation(self):
        """Test input validation for encoding."""
        grid = MaidenheadGrid(precision=2)

        # Test invalid latitudes
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            grid.encode(91, 0)

        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            grid.encode(-91, 0)

        # Test invalid longitudes
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            grid.encode(0, 181)

        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            grid.encode(0, -181)

    def test_get_cell_from_point(self):
        """Test getting cell from point coordinates."""
        grid = MaidenheadGrid(precision=3)
        cell = grid.get_cell_from_point(47.6062, -122.3321)

        assert cell.precision == 3
        assert isinstance(cell.identifier, str)
        assert len(cell.identifier) == 6  # Precision 3 = 6 characters
        assert cell.polygon.contains(Point(-122.3321, 47.6062))

    def test_get_cell_from_identifier(self):
        """Test getting cell from identifier."""
        grid = MaidenheadGrid(precision=2)

        # Test with known locator
        cell = grid.get_cell_from_identifier("CM87")

        assert cell.identifier == "CM87"
        assert cell.precision == 2

    def test_get_neighbors(self):
        """Test getting neighboring cells."""
        grid = MaidenheadGrid(precision=2)
        cell = grid.get_cell_from_point(47.6062, -122.3321)
        neighbors = grid.get_neighbors(cell)

        # Should have up to 8 neighbors
        assert len(neighbors) <= 8
        assert all(isinstance(neighbor, type(cell)) for neighbor in neighbors)
        assert all(neighbor.identifier != cell.identifier for neighbor in neighbors)

    def test_get_cells_in_bbox(self):
        """Test getting cells within bounding box."""
        grid = MaidenheadGrid(precision=1)

        # Bounding box covering part of Pacific Northwest
        min_lat, min_lon = 47.0, -123.0
        max_lat, max_lon = 48.0, -122.0

        cells = grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        assert len(cells) > 0
        assert all(
            isinstance(cell, type(grid.get_cell_from_point(47.5, -122.5)))
            for cell in cells
        )

    def test_precision_levels(self):
        """Test different precision levels."""
        test_lat, test_lon = 47.6062, -122.3321

        expected_lengths = {1: 2, 2: 4, 3: 6, 4: 8}

        for precision in range(1, 5):
            grid = MaidenheadGrid(precision=precision)
            cell = grid.get_cell_from_point(test_lat, test_lon)

            assert cell.precision == precision
            assert len(cell.identifier) == expected_lengths[precision]
            assert cell.polygon.contains(Point(test_lon, test_lat))

    def test_cell_area_decreases_with_precision(self):
        """Test that cell area decreases as precision increases."""
        test_lat, test_lon = 47.6062, -122.3321
        areas = []

        for precision in range(1, 5):
            grid = MaidenheadGrid(precision=precision)
            cell = grid.get_cell_from_point(test_lat, test_lon)
            areas.append(cell.area_km2)

        # Areas should decrease with higher precision
        for i in range(1, len(areas)):
            assert areas[i] < areas[i - 1]

    def test_decode_various_formats(self):
        """Test decoding various locator formats."""
        grid = MaidenheadGrid(precision=4)

        # Test different valid formats
        test_locators = [
            "CN87",  # Precision 2
            "CN87TW",  # Precision 3
            "CN87TW34",  # Precision 4
        ]

        for locator in test_locators:
            bounds = grid.decode(locator)
            assert len(bounds) == 4
            south, west, north, east = bounds
            assert south < north
            assert west < east

    def test_decode_invalid_input(self):
        """Test decoding with invalid input."""
        grid = MaidenheadGrid(precision=2)

        # Test too short
        with pytest.raises(ValueError, match="Locator must be at least 2 characters"):
            grid.decode("A")

    def test_worldwide_coverage(self):
        """Test that the grid works worldwide."""
        grid = MaidenheadGrid(precision=2)

        # Test various locations around the world
        test_locations = [
            (-34.6118, -58.3960),  # Buenos Aires
            (55.7558, 37.6176),  # Moscow
            (-33.8568, 151.2153),  # Sydney
            (19.4326, -99.1332),  # Mexico City
        ]

        for lat, lon in test_locations:
            cell = grid.get_cell_from_point(lat, lon)
            assert cell.polygon.contains(Point(lon, lat))
            assert len(cell.identifier) == 4  # Precision 2
