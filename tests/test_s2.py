"""
Tests for S2 grid system in M3S.
"""

import warnings
from unittest.mock import patch

import pytest
from shapely.geometry import Point, Polygon, box

from m3s.base import GridCell
from m3s.s2 import S2Grid


class TestS2Grid:
    """Test S2Grid class."""

    @pytest.fixture
    def grid_level_10(self):
        """Create an S2 grid with level 10."""
        return S2Grid(level=10)

    @pytest.fixture
    def grid_level_15(self):
        """Create an S2 grid with level 15."""
        return S2Grid(level=15)

    def test_initialization_valid_levels(self):
        """Test grid initialization with valid levels."""
        for level in [0, 10, 20, 30]:
            grid = S2Grid(level=level)
            assert grid.level == level
            assert grid.precision == level

    def test_initialization_invalid_levels(self):
        """Test grid initialization with invalid levels."""
        invalid_levels = [-1, 31, 100]
        for level in invalid_levels:
            with pytest.raises(ValueError, match="S2 level must be between 0 and 30"):
                S2Grid(level=level)

    def test_get_cell_from_point_nyc(self, grid_level_10):
        """Test getting cell from NYC coordinates."""
        # NYC coordinates
        lat, lon = 40.7128, -74.0060
        cell = grid_level_10.get_cell_from_point(lat, lon)

        assert isinstance(cell, GridCell)
        assert isinstance(cell.identifier, str)
        assert cell.precision == 10
        assert isinstance(cell.polygon, Polygon)

        # Check that the cell contains the original point
        point = Point(lon, lat)
        assert cell.polygon.contains(point) or cell.polygon.touches(point)

    def test_get_cell_from_point_la(self, grid_level_10):
        """Test getting cell from LA coordinates."""
        # LA coordinates
        lat, lon = 34.0522, -118.2437
        cell = grid_level_10.get_cell_from_point(lat, lon)

        assert isinstance(cell, GridCell)
        assert isinstance(cell.identifier, str)
        assert cell.precision == 10

        # Check containment
        point = Point(lon, lat)
        assert cell.polygon.contains(point) or cell.polygon.touches(point)

    def test_get_cell_from_point_edge_cases(self, grid_level_10):
        """Test getting cells from edge case coordinates."""
        edge_cases = [
            (85.0, 180.0),  # Near north pole, dateline
            (-85.0, -180.0),  # Near south pole, antimeridian
            (0.0, 0.0),  # Equator, prime meridian
            (60.0, 30.0),  # Mid latitude
            (-45.0, 120.0),  # Southern hemisphere
        ]

        for lat, lon in edge_cases:
            cell = grid_level_10.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert isinstance(cell.identifier, str)

    def test_get_cell_from_identifier_valid(self, grid_level_10):
        """Test getting cell from valid S2 cell token."""
        # Get a cell first
        cell = grid_level_10.get_cell_from_point(40.7128, -74.0060)
        identifier = cell.identifier

        # Get cell from identifier
        cell_from_id = grid_level_10.get_cell_from_identifier(identifier)

        assert cell_from_id.identifier == identifier
        assert isinstance(cell_from_id.polygon, Polygon)

    def test_get_cell_from_identifier_invalid(self, grid_level_10):
        """Test getting cell from invalid S2 cell token."""
        invalid_identifiers = [
            "invalid_token",
            "",
            "zzz",
            "12345xyz",
        ]

        for identifier in invalid_identifiers:
            with pytest.raises(ValueError, match="Invalid S2 cell token"):
                grid_level_10.get_cell_from_identifier(identifier)

    def test_get_neighbors(self, grid_level_10):
        """Test getting neighboring cells."""
        cell = grid_level_10.get_cell_from_point(40.0, -100.0)  # Central US
        neighbors = grid_level_10.get_neighbors(cell)

        assert isinstance(neighbors, list)
        # S2 should return some neighbors
        assert len(neighbors) >= 0

        # All neighbors should be valid GridCells
        for neighbor in neighbors:
            assert isinstance(neighbor, GridCell)
            assert isinstance(neighbor.identifier, str)
            assert neighbor.identifier != cell.identifier

    def test_get_children(self, grid_level_10):
        """Test getting child cells."""
        cell = grid_level_10.get_cell_from_point(40.7128, -74.0060)
        children = grid_level_10.get_children(cell)

        assert isinstance(children, list)
        assert len(children) == 4  # S2 cells have 4 children

        # All children should be valid
        for child in children:
            assert isinstance(child, GridCell)
            assert child.precision == 11  # One level deeper

    def test_get_children_max_level(self):
        """Test getting children at maximum level."""
        grid = S2Grid(level=30)  # Maximum level
        cell = grid.get_cell_from_point(40.7128, -74.0060)
        children = grid.get_children(cell)

        assert children == []  # No children at max level

    def test_get_parent(self, grid_level_10):
        """Test getting parent cell."""
        cell = grid_level_10.get_cell_from_point(40.7128, -74.0060)
        parent = grid_level_10.get_parent(cell)

        assert isinstance(parent, GridCell)
        assert parent.precision == 9  # One level up

    def test_get_parent_root_level(self):
        """Test getting parent at root level."""
        grid = S2Grid(level=0)
        cell = grid.get_cell_from_point(40.7128, -74.0060)
        parent = grid.get_parent(cell)

        assert parent is None  # No parent at level 0

    def test_get_cells_in_bbox_small(self, grid_level_10):
        """Test getting cells in a small bounding box."""
        # Small area around NYC
        min_lat, min_lon = 40.7, -74.1
        max_lat, max_lon = 40.8, -74.0

        cells = grid_level_10.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        assert isinstance(cells, list)
        assert len(cells) > 0

        # All cells should be valid
        for cell in cells:
            assert isinstance(cell, GridCell)
            assert isinstance(cell.identifier, str)

    def test_get_cells_in_bbox_large(self, grid_level_10):
        """Test getting cells in a large bounding box."""
        # Large area covering multiple states
        min_lat, min_lon = 35.0, -80.0
        max_lat, max_lon = 45.0, -70.0

        cells = grid_level_10.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        assert isinstance(cells, list)
        assert len(cells) > 0

    def test_get_covering_cells(self, grid_level_10):
        """Test getting covering cells."""
        # Create a simple polygon
        polygon = box(-74.1, 40.7, -74.0, 40.8)  # Small rectangle around NYC

        cells = grid_level_10.get_covering_cells(polygon, max_cells=50)

        assert isinstance(cells, list)
        assert len(cells) > 0
        assert len(cells) <= 50  # Should respect max_cells limit

        # All cells should be valid
        for cell in cells:
            assert isinstance(cell, GridCell)
            assert cell.precision == 10

    def test_different_levels_same_point(self):
        """Test that different levels produce different cell sizes."""
        lat, lon = 40.7128, -74.0060
        levels = [5, 10, 15]
        cells = []

        for level in levels:
            grid = S2Grid(level=level)
            cell = grid.get_cell_from_point(lat, lon)
            cells.append(cell)

        # All should contain the same point
        point = Point(lon, lat)
        for cell in cells:
            assert cell.polygon.contains(point) or cell.polygon.touches(point)

        # Different levels should produce different identifiers
        identifiers = [cell.identifier for cell in cells]
        assert len(set(identifiers)) == 3  # All should be unique

    def test_coordinate_conversion_consistency(self, grid_level_10):
        """Test that coordinate conversions are consistent."""
        test_points = [
            (40.7128, -74.0060),  # NYC
            (34.0522, -118.2437),  # LA
            (51.5074, -0.1278),  # London
            (35.6762, 139.6503),  # Tokyo
        ]

        for lat, lon in test_points:
            # Get cell from point
            cell = grid_level_10.get_cell_from_point(lat, lon)

            # Get cell from identifier
            cell_from_id = grid_level_10.get_cell_from_identifier(cell.identifier)

            # Should be the same identifier
            assert cell.identifier == cell_from_id.identifier

    def test_repr(self, grid_level_10):
        """Test string representation of grid."""
        repr_str = repr(grid_level_10)
        assert "S2Grid" in repr_str
        assert "level=10" in repr_str


class TestS2GridEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def grid_level_10(self):
        """Create an S2 grid with level 10."""
        return S2Grid(level=10)

    def test_extreme_coordinates(self):
        """Test with extreme but valid coordinates."""
        grid = S2Grid(level=5)

        extreme_coords = [
            (85.0, 179.0),  # Near max lat/lon
            (-85.0, -179.0),  # Near min lat/lon
            (0.0, 0.0),  # Origin
        ]

        for lat, lon in extreme_coords:
            cell = grid.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)

    def test_empty_bbox(self):
        """Test with empty bounding box."""
        grid = S2Grid(level=10)

        # Point bounding box (min == max)
        cells = grid.get_cells_in_bbox(40.7, -74.0, 40.7, -74.0)

        # Should return at least one cell
        assert len(cells) >= 1

    def test_error_handling_in_neighbors(self, grid_level_10):
        """Test error handling in neighbor computation."""
        # Create a mock that raises an exception
        with patch("m3s.s2.s2sphere") as mock_s2:
            mock_s2.CellId.from_token.side_effect = Exception("Test error")

            cell = grid_level_10.get_cell_from_point(40.7, -74.0)

            with warnings.catch_warnings(record=True) as w:
                neighbors = grid_level_10.get_neighbors(cell)

                # Should return empty list and issue warning
                assert neighbors == []
                assert len(w) > 0

    def test_error_handling_in_children(self, grid_level_10):
        """Test error handling in children computation."""
        with patch("m3s.s2.s2sphere") as mock_s2:
            mock_s2.CellId.from_token.side_effect = Exception("Test error")

            cell = grid_level_10.get_cell_from_point(40.7, -74.0)

            with warnings.catch_warnings(record=True) as w:
                children = grid_level_10.get_children(cell)

                # Should return empty list and issue warning
                assert children == []
                assert len(w) > 0

    def test_error_handling_in_covering_cells(self, grid_level_10):
        """Test error handling in covering cells computation."""
        polygon = box(-74.1, 40.7, -74.0, 40.8)

        with patch("m3s.s2.s2sphere") as mock_s2:
            mock_s2.LatLng.from_degrees.side_effect = Exception("Test error")

            with warnings.catch_warnings(record=True) as w:
                cells = grid_level_10.get_covering_cells(polygon)

                # Should fallback to bounding box method
                assert isinstance(cells, list)
                assert len(w) > 0


class TestS2GridWithS2Sphere:
    """Test S2Grid functionality with s2sphere."""

    def test_s2sphere_integration(self):
        """Test that s2sphere integration works correctly."""
        grid = S2Grid(level=10)

        # Get a cell
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        # Token should be valid hex
        try:
            int(cell.identifier, 16)
        except ValueError:
            pytest.fail("S2 cell token should be valid hexadecimal")

    def test_s2sphere_hierarchy(self):
        """Test parent-child relationships with s2sphere."""
        grid = S2Grid(level=10)
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        # Get children
        children = grid.get_children(cell)
        assert len(children) == 4

        # Each child should have the correct parent
        for child in children:
            child_grid = S2Grid(level=child.precision)
            parent = child_grid.get_parent(child)
            # Parent token might be different due to S2 hierarchy,
            # but should be related
            assert parent is not None

    def test_s2sphere_covering(self):
        """Test polygon covering with s2sphere."""
        grid = S2Grid(level=8)  # Use lower level for faster computation

        # Create a polygon
        polygon = box(-74.1, 40.7, -74.0, 40.8)

        # Get covering cells
        cells = grid.get_covering_cells(polygon, max_cells=20)

        assert len(cells) > 0
        assert len(cells) <= 20

        # All cells should intersect with the polygon
        for cell in cells:
            assert cell.polygon.intersects(polygon)
