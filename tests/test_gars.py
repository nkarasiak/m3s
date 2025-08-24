"""
Tests for GARS (Global Area Reference System) grid implementation.
"""

import pytest
from shapely.geometry import Point

from m3s import GARSGrid


class TestGARSGrid:
    """Test suite for GARSGrid."""

    def test_init_valid_precision(self):
        """Test grid initialization with valid precision."""
        grid = GARSGrid(precision=2)
        assert grid.precision == 2

    def test_init_invalid_precision(self):
        """Test grid initialization with invalid precision."""
        with pytest.raises(ValueError, match="GARS precision must be between 1 and 3"):
            GARSGrid(precision=0)

        with pytest.raises(ValueError, match="GARS precision must be between 1 and 3"):
            GARSGrid(precision=4)

    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding are consistent."""
        grid = GARSGrid(precision=2)
        lat, lon = 39.0458, -76.6413  # Baltimore

        gars_id = grid.encode(lat, lon)
        south, west, north, east = grid.decode(gars_id)

        # Original point should be within decoded bounds
        assert south <= lat <= north
        assert west <= lon <= east

    def test_encode_known_locations(self):
        """Test encoding of known locations."""
        grid = GARSGrid(precision=1)

        # Test various locations
        test_cases = [
            (39.0458, -76.6413),  # Baltimore
            (51.5074, -0.1278),  # London
            (35.6762, 139.6503),  # Tokyo
            (0.0, 0.0),  # Null Island
        ]

        for lat, lon in test_cases:
            gars_id = grid.encode(lat, lon)
            assert isinstance(gars_id, str)
            assert len(gars_id) == 5  # Precision 1 = 5 characters (LLLAA)

    def test_encode_input_validation(self):
        """Test input validation for encoding."""
        grid = GARSGrid(precision=1)

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
        grid = GARSGrid(precision=2)
        cell = grid.get_cell_from_point(39.0458, -76.6413)

        assert cell.precision == 2
        assert isinstance(cell.identifier, str)
        assert len(cell.identifier) == 6  # Precision 2 = 6 characters
        assert cell.polygon.contains(Point(-76.6413, 39.0458))

    def test_get_cell_from_identifier(self):
        """Test getting cell from identifier."""
        grid = GARSGrid(precision=1)

        # Get a cell first
        original_cell = grid.get_cell_from_point(39.0458, -76.6413)

        # Get same cell from identifier
        retrieved_cell = grid.get_cell_from_identifier(original_cell.identifier)

        assert retrieved_cell.identifier == original_cell.identifier
        assert retrieved_cell.precision == original_cell.precision

    def test_get_neighbors(self):
        """Test getting neighboring cells."""
        grid = GARSGrid(precision=1)
        cell = grid.get_cell_from_point(39.0458, -76.6413)
        neighbors = grid.get_neighbors(cell)

        # Should have up to 8 neighbors
        assert len(neighbors) <= 8
        assert all(isinstance(neighbor, type(cell)) for neighbor in neighbors)
        assert all(neighbor.identifier != cell.identifier for neighbor in neighbors)

    def test_get_cells_in_bbox(self):
        """Test getting cells within bounding box."""
        grid = GARSGrid(precision=1)

        # Bounding box around Washington DC area
        min_lat, min_lon = 38.8, -77.1
        max_lat, max_lon = 39.1, -76.9

        cells = grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        assert len(cells) > 0
        assert all(
            isinstance(cell, type(grid.get_cell_from_point(39.0, -77.0)))
            for cell in cells
        )

    def test_precision_levels(self):
        """Test different precision levels."""
        test_lat, test_lon = 39.0458, -76.6413

        expected_lengths = {1: 5, 2: 6, 3: 7}

        for precision in range(1, 4):
            grid = GARSGrid(precision=precision)
            cell = grid.get_cell_from_point(test_lat, test_lon)

            assert cell.precision == precision
            assert len(cell.identifier) == expected_lengths[precision]
            assert cell.polygon.contains(Point(test_lon, test_lat))

    def test_cell_area_decreases_with_precision(self):
        """Test that cell area decreases as precision increases."""
        test_lat, test_lon = 39.0458, -76.6413
        areas = []

        for precision in range(1, 4):
            grid = GARSGrid(precision=precision)
            cell = grid.get_cell_from_point(test_lat, test_lon)
            areas.append(cell.area_km2)

        # Areas should decrease with higher precision
        for i in range(1, len(areas)):
            assert areas[i] < areas[i - 1]

    def test_decode_various_formats(self):
        """Test decoding various GARS formats."""
        grid = GARSGrid(precision=3)

        # Test different valid formats
        test_gars_ids = [
            "189LV",  # Precision 1
            "189LV2",  # Precision 2
            "189LV24",  # Precision 3
        ]

        for gars_id in test_gars_ids:
            bounds = grid.decode(gars_id)
            assert len(bounds) == 4
            south, west, north, east = bounds
            assert south < north
            assert west < east

    def test_decode_invalid_input(self):
        """Test decoding with invalid input."""
        grid = GARSGrid(precision=1)

        # Test too short
        with pytest.raises(ValueError, match="GARS ID must be at least 5 characters"):
            grid.decode("189L")

        # Test invalid longitude band
        with pytest.raises(ValueError, match="Invalid longitude band"):
            grid.decode("000AA")

        with pytest.raises(ValueError, match="Invalid longitude band"):
            grid.decode("721AA")

    def test_quadrant_encoding(self):
        """Test quadrant encoding for precision 2."""
        grid = GARSGrid(precision=2)

        # Test that quadrants are assigned correctly
        test_lat, test_lon = 39.0458, -76.6413
        gars_id = grid.encode(test_lat, test_lon)

        # Should have quadrant digit (1-4) at the end
        assert len(gars_id) == 6
        assert gars_id[-1] in "1234"

    def test_keypad_encoding(self):
        """Test keypad encoding for precision 3."""
        grid = GARSGrid(precision=3)

        # Test that keypad digits are assigned correctly
        test_lat, test_lon = 39.0458, -76.6413
        gars_id = grid.encode(test_lat, test_lon)

        # Should have keypad digit (1-9) at the end
        assert len(gars_id) == 7
        assert gars_id[-1] in "123456789"

    def test_worldwide_coverage(self):
        """Test that the grid works worldwide."""
        grid = GARSGrid(precision=1)

        # Test various locations around the world
        test_locations = [
            (-34.6118, -58.3960),  # Buenos Aires
            (55.7558, 37.6176),  # Moscow
            (-33.8568, 151.2153),  # Sydney
            (19.4326, -99.1332),  # Mexico City
            (64.2008, -149.4937),  # Fairbanks, Alaska
            (-77.8456, 166.6685),  # McMurdo Station, Antarctica
        ]

        for lat, lon in test_locations:
            cell = grid.get_cell_from_point(lat, lon)
            assert cell.polygon.contains(Point(lon, lat))
            assert len(cell.identifier) == 5  # Precision 1

    def test_longitude_band_calculation(self):
        """Test longitude band calculation."""
        grid = GARSGrid(precision=1)

        # Test specific longitude values
        test_cases = [
            (-180, 1),  # Western edge
            (-179.5, 2),  # Second band
            (0, 361),  # Prime meridian
            (179.5, 720),  # Eastern edge
        ]

        for lon, expected_band in test_cases:
            gars_id = grid.encode(0, lon)  # Use equator for latitude
            band = int(gars_id[:3])
            assert band == expected_band

    def test_latitude_zone_calculation(self):
        """Test latitude zone calculation."""
        grid = GARSGrid(precision=1)

        # Test that latitude zones work correctly
        test_lat = 39.0  # Should be in a specific zone
        gars_id = grid.encode(test_lat, 0)

        # Should have proper letter encoding
        letters = gars_id[3:5]
        assert len(letters) == 2
        assert all(c.isalpha() for c in letters)
