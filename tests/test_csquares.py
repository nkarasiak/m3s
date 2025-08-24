"""
Tests for C-squares grid implementation.
"""

import pytest
from shapely.geometry import Polygon

from m3s import CSquaresGrid
from m3s.base import GridCell


class TestCSquaresGrid:
    """Test CSquaresGrid functionality."""

    def test_init_default(self):
        """Test default initialization."""
        grid = CSquaresGrid()
        assert grid.precision == 3

    def test_init_custom_precision(self):
        """Test initialization with custom precision."""
        grid = CSquaresGrid(precision=2)
        assert grid.precision == 2

    def test_init_invalid_precision(self):
        """Test initialization with invalid precision."""
        with pytest.raises(
            ValueError, match="C-squares precision must be between 1 and 5"
        ):
            CSquaresGrid(precision=0)

        with pytest.raises(
            ValueError, match="C-squares precision must be between 1 and 5"
        ):
            CSquaresGrid(precision=6)

    def test_get_cell_from_point_valid(self):
        """Test getting cell from valid coordinates."""
        grid = CSquaresGrid(precision=3)

        # Test point in Northeast quadrant (positive lat, positive lon)
        cell = grid.get_cell_from_point(40.7, 74.0)
        assert isinstance(cell, GridCell)
        assert cell.identifier.startswith("1")  # Northeast quadrant

        # Test point in Northwest quadrant (positive lat, negative lon)
        cell = grid.get_cell_from_point(40.7, -74.0)
        assert isinstance(cell, GridCell)
        assert cell.identifier.startswith("3")  # Northwest quadrant

        # Test point in Southwest quadrant (negative lat, negative lon)
        cell = grid.get_cell_from_point(-40.7, -74.0)
        assert isinstance(cell, GridCell)
        assert cell.identifier.startswith("5")  # Southwest quadrant

        # Test point in Southeast quadrant (negative lat, positive lon)
        cell = grid.get_cell_from_point(-40.7, 74.0)
        assert isinstance(cell, GridCell)
        assert cell.identifier.startswith("7")  # Southeast quadrant

    def test_get_cell_from_point_invalid_coordinates(self):
        """Test getting cell from invalid coordinates."""
        grid = CSquaresGrid(precision=3)

        # Invalid latitude
        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            grid.get_cell_from_point(91.0, 0.0)

        with pytest.raises(ValueError, match="Latitude must be between -90 and 90"):
            grid.get_cell_from_point(-91.0, 0.0)

        # Invalid longitude
        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            grid.get_cell_from_point(0.0, 181.0)

        with pytest.raises(ValueError, match="Longitude must be between -180 and 180"):
            grid.get_cell_from_point(0.0, -181.0)

    def test_get_cell_from_identifier_valid(self):
        """Test getting cell from valid identifier."""
        grid = CSquaresGrid(precision=3)

        # Test valid C-squares identifier
        cell = grid.get_cell_from_identifier("1403:00:00")
        assert isinstance(cell, GridCell)
        assert isinstance(cell.polygon, Polygon)
        assert cell.precision == 3

    def test_get_cell_from_identifier_invalid(self):
        """Test getting cell from invalid identifier."""
        grid = CSquaresGrid(precision=3)

        with pytest.raises(ValueError, match="Invalid C-squares identifier"):
            grid.get_cell_from_identifier("invalid")

    def test_encode_decode_consistency(self):
        """Test that encoding and decoding are consistent."""
        grid = CSquaresGrid(precision=3)

        test_points = [
            (40.7, -74.0),  # NYC
            (34.0, -118.2),  # LA
            (51.5, -0.1),  # London
            (-33.9, 151.2),  # Sydney
            (0.0, 0.0),  # Null Island
        ]

        for lat, lon in test_points:
            # Get cell from point
            cell = grid.get_cell_from_point(lat, lon)

            # Decode the identifier
            min_lat, min_lon, max_lat, max_lon = grid._decode_csquare(cell.identifier)

            # Check that original point is within decoded bounds
            assert min_lat <= lat <= max_lat
            assert min_lon <= lon <= max_lon

            # Check that polygon bounds match decoded bounds
            bounds = cell.polygon.bounds
            assert abs(bounds[0] - min_lon) < 1e-10
            assert abs(bounds[1] - min_lat) < 1e-10
            assert abs(bounds[2] - max_lon) < 1e-10
            assert abs(bounds[3] - max_lat) < 1e-10

    def test_get_neighbors(self):
        """Test getting neighboring cells."""
        grid = CSquaresGrid(precision=3)

        # Get a cell not at the edge
        cell = grid.get_cell_from_point(40.0, -74.0)
        neighbors = grid.get_neighbors(cell)

        # Should have up to 8 neighbors
        assert len(neighbors) <= 8
        assert all(isinstance(n, GridCell) for n in neighbors)

        # All neighbors should be different from the original cell
        neighbor_ids = [n.identifier for n in neighbors]
        assert cell.identifier not in neighbor_ids

        # All neighbor identifiers should be unique
        assert len(neighbor_ids) == len(set(neighbor_ids))

    def test_get_neighbors_edge_cases(self):
        """Test getting neighbors for edge cases."""
        grid = CSquaresGrid(precision=3)

        # Test cell near edge (should have fewer neighbors)
        edge_cell = grid.get_cell_from_point(89.0, 179.0)
        neighbors = grid.get_neighbors(edge_cell)

        # Should still return some neighbors, but likely fewer than 8
        assert isinstance(neighbors, list)
        assert all(isinstance(n, GridCell) for n in neighbors)

    def test_get_cells_in_bbox(self):
        """Test getting cells within bounding box."""
        grid = CSquaresGrid(precision=3)

        # Test small bounding box
        cells = grid.get_cells_in_bbox(40.0, -75.0, 41.0, -74.0)

        assert isinstance(cells, list)
        assert len(cells) >= 1
        assert all(isinstance(cell, GridCell) for cell in cells)

        # Check that all cells intersect with the bounding box
        bbox_polygon = Polygon(
            [(-75.0, 40.0), (-74.0, 40.0), (-74.0, 41.0), (-75.0, 41.0), (-75.0, 40.0)]
        )

        for cell in cells:
            assert cell.polygon.intersects(bbox_polygon)

    def test_get_precision_info(self):
        """Test precision information retrieval."""
        for precision in range(1, 6):
            grid = CSquaresGrid(precision=precision)
            info = grid.get_precision_info()

            assert info["precision"] == precision
            assert isinstance(info["cell_size_degrees"], float)
            assert isinstance(info["cell_size_km"], float)
            assert isinstance(info["total_global_cells"], int)
            assert isinstance(info["description"], str)

            # Check that cell size decreases with higher precision
            if precision > 1:
                smaller_grid = CSquaresGrid(precision=precision)
                larger_grid = CSquaresGrid(precision=precision - 1)
                assert (
                    smaller_grid.get_precision_info()["cell_size_degrees"]
                    < larger_grid.get_precision_info()["cell_size_degrees"]
                )

    def test_area_km2_property(self):
        """Test area calculation property."""
        for precision in range(1, 6):
            grid = CSquaresGrid(precision=precision)
            area = grid.area_km2

            assert isinstance(area, float)
            assert area > 0

            # Higher precision should have smaller area
            if precision > 1:
                larger_grid = CSquaresGrid(precision=precision - 1)
                assert area < larger_grid.area_km2

    def test_different_precision_levels(self):
        """Test different precision levels produce different cell sizes."""
        point = (40.7, -74.0)

        cells = {}
        for precision in range(1, 6):
            grid = CSquaresGrid(precision=precision)
            cell = grid.get_cell_from_point(*point)
            cells[precision] = cell

            # Check identifier format varies with precision
            parts = cell.identifier.split(":")
            assert len(parts) == precision

        # Higher precision cells should be smaller
        for i in range(1, 5):
            area_i = cells[i].polygon.area
            area_next = cells[i + 1].polygon.area
            assert area_next < area_i

    def test_boundary_conditions(self):
        """Test boundary conditions and edge cases."""
        grid = CSquaresGrid(precision=3)

        # Test points at coordinate system boundaries
        boundary_points = [
            (0.0, 0.0),  # Origin
            (90.0, 180.0),  # North-East corner
            (-90.0, -180.0),  # South-West corner
            (90.0, -180.0),  # North-West corner
            (-90.0, 180.0),  # South-East corner
        ]

        for lat, lon in boundary_points:
            cell = grid.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert isinstance(cell.polygon, Polygon)

    def test_identifier_format(self):
        """Test C-squares identifier format."""
        grid = CSquaresGrid(precision=3)

        cell = grid.get_cell_from_point(40.7, -74.0)
        identifier = cell.identifier

        # Should start with quadrant number
        assert identifier[0] in "1357"

        # Should have correct number of parts separated by colons
        parts = identifier.split(":")
        assert len(parts) == 3  # For precision 3

        # Base part should have correct format (quadrant + lat + lon)
        base_part = parts[0]
        assert len(base_part) == 4  # 1 digit quadrant + 1 digit lat + 2 digit lon

    def test_precision_from_identifier(self):
        """Test precision determination from identifier."""
        grid = CSquaresGrid(precision=1)

        # Test different identifier formats
        test_cases = [
            ("1403", 1),
            ("1403:00", 2),
            ("1403:00:00", 3),
            ("1403:00:00:00", 4),
            ("1403:00:00:00:00", 5),
        ]

        for identifier, expected_precision in test_cases:
            precision = grid._get_precision_from_identifier(identifier)
            assert precision == expected_precision

    def test_cell_size_consistency(self):
        """Test that cell sizes are consistent across the system."""
        expected_sizes = {1: 10.0, 2: 5.0, 3: 1.0, 4: 0.5, 5: 0.1}

        for precision, expected_size in expected_sizes.items():
            grid = CSquaresGrid(precision=precision)
            assert grid._get_cell_size(precision) == expected_size

    def test_roundtrip_encode_decode(self):
        """Test that encode->decode->encode produces same result."""
        grid = CSquaresGrid(precision=4)

        # Test various points
        test_points = [
            (45.5, -73.5),  # Montreal
            (-34.6, -58.4),  # Buenos Aires
            (35.7, 139.7),  # Tokyo
            (55.8, 37.6),  # Moscow
        ]

        for lat, lon in test_points:
            # Encode to identifier
            identifier1 = grid._encode_csquare(lat, lon, grid.precision)

            # Decode to bounds
            min_lat, min_lon, max_lat, max_lon = grid._decode_csquare(identifier1)

            # Take center point of decoded cell
            center_lat = (min_lat + max_lat) / 2
            center_lon = (min_lon + max_lon) / 2

            # Encode center point
            identifier2 = grid._encode_csquare(center_lat, center_lon, grid.precision)

            # Should produce same identifier
            assert identifier1 == identifier2

    def test_get_neighbors_exception_handling(self):
        """Test neighbor finding with invalid cells."""
        grid = CSquaresGrid(precision=3)

        # Create an invalid cell that would cause exceptions
        invalid_cell = GridCell(
            "invalid:format", Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)]), 3
        )

        # Should return empty list when exceptions occur
        neighbors = grid.get_neighbors(invalid_cell)
        assert neighbors == []

    def test_decode_csquare_edge_cases(self):
        """Test edge cases in C-squares decoding."""
        grid = CSquaresGrid(precision=3)

        # Test empty identifier (triggers base identifier error due to empty string)
        with pytest.raises(ValueError, match="Invalid C-squares base identifier"):
            grid._decode_csquare("")

        # Test identifier with no meaningful parts
        with pytest.raises(ValueError, match="Invalid C-squares base identifier"):
            grid._decode_csquare(":")

        # Test base part too short
        with pytest.raises(ValueError, match="Invalid C-squares base identifier"):
            grid._decode_csquare("14")

        # Test invalid base format (wrong length)
        with pytest.raises(ValueError, match="Invalid C-squares base format"):
            grid._decode_csquare("14031")  # 5 chars instead of 4

        # Test invalid quadrant
        with pytest.raises(ValueError, match="Invalid quadrant"):
            grid._decode_csquare("2403:00:00")  # Quadrant 2 is invalid

        # Test invalid subdivision part
        with pytest.raises(ValueError, match="Invalid subdivision part"):
            grid._decode_csquare("1403:0:00")  # Single digit instead of 2
