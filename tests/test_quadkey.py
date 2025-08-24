"""
Tests for Quadkey grid system in M3S.
"""

import pytest
from shapely.geometry import Point, Polygon, box

from m3s.base import GridCell
from m3s.quadkey import QuadkeyGrid


class TestQuadkeyGrid:
    """Test QuadkeyGrid class."""

    @pytest.fixture
    def grid_level_10(self):
        """Create a Quadkey grid with level 10."""
        return QuadkeyGrid(level=10)

    @pytest.fixture
    def grid_level_15(self):
        """Create a Quadkey grid with level 15."""
        return QuadkeyGrid(level=15)

    def test_initialization_valid_levels(self):
        """Test grid initialization with valid levels."""
        for level in [1, 10, 15, 23]:
            grid = QuadkeyGrid(level=level)
            assert grid.level == level
            assert grid.precision == level

    def test_initialization_invalid_levels(self):
        """Test grid initialization with invalid levels."""
        invalid_levels = [0, 24, -1, 100]
        for level in invalid_levels:
            with pytest.raises(
                ValueError, match="Quadkey level must be between 1 and 23"
            ):
                QuadkeyGrid(level=level)

    def test_get_cell_from_point_nyc(self, grid_level_10):
        """Test getting cell from NYC coordinates."""
        # NYC coordinates
        lat, lon = 40.7128, -74.0060
        cell = grid_level_10.get_cell_from_point(lat, lon)

        assert isinstance(cell, GridCell)
        assert isinstance(cell.identifier, str)
        assert len(cell.identifier) == 10  # Same as level
        assert all(c in "0123" for c in cell.identifier)
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
        assert len(cell.identifier) == 10
        assert all(c in "0123" for c in cell.identifier)

        # Check containment
        point = Point(lon, lat)
        assert cell.polygon.contains(point) or cell.polygon.touches(point)

    def test_get_cell_from_point_edge_cases(self, grid_level_10):
        """Test getting cells from edge case coordinates."""
        edge_cases = [
            (85.05, 180.0),  # Near north pole, dateline
            (-85.05, -180.0),  # Near south pole, antimeridian
            (0.0, 0.0),  # Equator, prime meridian
            (85.0, 0.0),  # Near north pole, prime meridian
            (-85.0, 0.0),  # Near south pole, prime meridian
        ]

        for lat, lon in edge_cases:
            cell = grid_level_10.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert len(cell.identifier) == 10
            assert all(c in "0123" for c in cell.identifier)

    def test_get_cell_from_identifier_valid(self, grid_level_10):
        """Test getting cell from valid quadkey identifier."""
        # Get a cell first
        cell = grid_level_10.get_cell_from_point(40.7128, -74.0060)
        identifier = cell.identifier

        # Get cell from identifier
        cell_from_id = grid_level_10.get_cell_from_identifier(identifier)

        assert cell_from_id.identifier == identifier
        assert cell_from_id.precision == 10
        assert isinstance(cell_from_id.polygon, Polygon)

        # Polygons should be the same
        assert cell.polygon.equals(cell_from_id.polygon)

    def test_get_cell_from_identifier_invalid_length(self, grid_level_10):
        """Test getting cell from identifier with wrong length."""
        invalid_identifiers = [
            "123",  # Too short
            "12345678901",  # Too long
            "",  # Empty
        ]

        for identifier in invalid_identifiers:
            with pytest.raises(
                ValueError, match="Quadkey length .* does not match grid level"
            ):
                grid_level_10.get_cell_from_identifier(identifier)

    def test_get_cell_from_identifier_invalid_digits(self, grid_level_10):
        """Test getting cell from identifier with invalid digits."""
        invalid_identifiers = [
            "123456789a",  # Contains letter
            "1234567894",  # Contains 4
            "123456789-",  # Contains special character
        ]

        for identifier in invalid_identifiers:
            with pytest.raises(
                ValueError, match="Quadkey must contain only digits 0, 1, 2, 3"
            ):
                grid_level_10.get_cell_from_identifier(identifier)

    def test_get_neighbors(self, grid_level_10):
        """Test getting neighboring cells."""
        # Get a cell from a central location
        cell = grid_level_10.get_cell_from_point(40.0, -100.0)  # Central US
        neighbors = grid_level_10.get_neighbors(cell)

        assert isinstance(neighbors, list)
        assert len(neighbors) <= 8  # Maximum 8 neighbors
        assert len(neighbors) >= 3  # Should have at least 3 neighbors for most cells

        # All neighbors should be valid GridCells
        for neighbor in neighbors:
            assert isinstance(neighbor, GridCell)
            assert len(neighbor.identifier) == 10
            assert all(c in "0123" for c in neighbor.identifier)
            assert (
                neighbor.identifier != cell.identifier
            )  # Should be different from original

    def test_get_neighbors_edge_cell(self, grid_level_10):
        """Test getting neighbors for a cell at the edge of the world."""
        # Get a cell near the edge (high latitude)
        cell = grid_level_10.get_cell_from_point(80.0, 0.0)
        neighbors = grid_level_10.get_neighbors(cell)

        assert isinstance(neighbors, list)
        # Edge cells will have fewer neighbors
        assert len(neighbors) >= 0
        assert len(neighbors) <= 8

    def test_get_children(self, grid_level_10):
        """Test getting child cells."""
        cell = grid_level_10.get_cell_from_point(40.7128, -74.0060)
        children = grid_level_10.get_children(cell)

        assert isinstance(children, list)
        assert len(children) == 4  # Quadkey always has 4 children

        # All children should be valid
        for child in children:
            assert isinstance(child, GridCell)
            assert len(child.identifier) == 11  # One level deeper
            assert child.identifier.startswith(
                cell.identifier
            )  # Should be prefixed by parent
            assert child.precision == 11

    def test_get_children_max_level(self):
        """Test getting children at maximum level."""
        grid = QuadkeyGrid(level=23)  # Maximum level
        cell = grid.get_cell_from_point(40.7128, -74.0060)
        children = grid.get_children(cell)

        assert children == []  # No children at max level

    def test_get_parent(self, grid_level_10):
        """Test getting parent cell."""
        cell = grid_level_10.get_cell_from_point(40.7128, -74.0060)
        parent = grid_level_10.get_parent(cell)

        assert isinstance(parent, GridCell)
        assert len(parent.identifier) == 9  # One level up
        assert cell.identifier.startswith(
            parent.identifier
        )  # Child should be prefixed by parent
        assert parent.precision == 9

    def test_get_parent_root_level(self):
        """Test getting parent at root level."""
        grid = QuadkeyGrid(level=1)
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        with pytest.raises(ValueError, match="Cell has no parent"):
            grid.get_parent(cell)

    def test_get_cells_in_bbox_small(self, grid_level_10):
        """Test getting cells in a small bounding box."""
        # Small area around NYC
        min_lat, min_lon = 40.7, -74.1
        max_lat, max_lon = 40.8, -74.0

        cells = grid_level_10.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        assert isinstance(cells, list)
        assert len(cells) > 0
        assert len(cells) < 100  # Should be reasonable number for small area

        # All cells should be valid
        for cell in cells:
            assert isinstance(cell, GridCell)
            assert len(cell.identifier) == 10
            assert all(c in "0123" for c in cell.identifier)

    def test_get_cells_in_bbox_large(self, grid_level_10):
        """Test getting cells in a large bounding box."""
        # Large area covering multiple states
        min_lat, min_lon = 35.0, -80.0
        max_lat, max_lon = 45.0, -70.0

        cells = grid_level_10.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        assert isinstance(cells, list)
        assert len(cells) > 10  # Should have many cells for large area

        # Check that all cells are within or near the bounding box
        bbox = box(min_lon, min_lat, max_lon, max_lat)
        for cell in cells:
            # Cell should intersect with bounding box
            assert cell.polygon.intersects(bbox)

    def test_get_quadkey_bounds(self, grid_level_10):
        """Test getting bounds of a quadkey."""
        # Get a cell and its quadkey
        cell = grid_level_10.get_cell_from_point(40.7128, -74.0060)
        quadkey = cell.identifier

        bounds = grid_level_10.get_quadkey_bounds(quadkey)

        assert isinstance(bounds, tuple)
        assert len(bounds) == 4
        min_lat, min_lon, max_lat, max_lon = bounds

        # Bounds should be valid
        assert min_lat < max_lat
        assert min_lon < max_lon
        assert -90 <= min_lat <= 90
        assert -90 <= max_lat <= 90
        assert -180 <= min_lon <= 180
        assert -180 <= max_lon <= 180

        # Original point should be within bounds
        assert min_lat <= 40.7128 <= max_lat
        assert min_lon <= -74.0060 <= max_lon

    def test_different_levels_same_point(self):
        """Test that different levels produce different cell sizes."""
        lat, lon = 40.7128, -74.0060
        levels = [5, 10, 15]
        cells = []

        for level in levels:
            grid = QuadkeyGrid(level=level)
            cell = grid.get_cell_from_point(lat, lon)
            cells.append(cell)

        # All should contain the same point
        point = Point(lon, lat)
        for cell in cells:
            assert cell.polygon.contains(point) or cell.polygon.touches(point)

        # Higher level cells should be smaller
        areas = [cell.polygon.area for cell in cells]
        assert areas[0] > areas[1] > areas[2]  # Level 5 > Level 10 > Level 15

        # Higher level quadkeys should be longer
        lengths = [len(cell.identifier) for cell in cells]
        assert lengths == [5, 10, 15]

    def test_cell_hierarchy(self, grid_level_10):
        """Test that parent-child relationships work correctly."""
        # Get a cell
        cell = grid_level_10.get_cell_from_point(40.7128, -74.0060)

        # Get its children
        children = grid_level_10.get_children(cell)

        # Each child's parent should be the original cell
        for child in children:
            # Create a grid at the child's level to get parent
            child_grid = QuadkeyGrid(level=child.precision)
            parent = child_grid.get_parent(child)
            assert parent.identifier == cell.identifier

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

            # Should be the same
            assert cell.identifier == cell_from_id.identifier
            assert cell.polygon.equals(cell_from_id.polygon)

    def test_pixel_tile_conversions(self, grid_level_10):
        """Test internal pixel and tile coordinate conversions."""
        lat, lon = 40.7128, -74.0060

        # Test lat/lon to pixel conversion
        pixel_x, pixel_y = grid_level_10._lat_lon_to_pixel_xy(lat, lon)
        assert isinstance(pixel_x, int)
        assert isinstance(pixel_y, int)
        assert pixel_x >= 0
        assert pixel_y >= 0

        # Test pixel to tile conversion
        tile_x, tile_y = grid_level_10._pixel_xy_to_tile_xy(pixel_x, pixel_y)
        assert isinstance(tile_x, int)
        assert isinstance(tile_y, int)
        assert tile_x >= 0
        assert tile_y >= 0

        # Test tile to quadkey conversion
        quadkey = grid_level_10._tile_xy_to_quadkey(tile_x, tile_y)
        assert isinstance(quadkey, str)
        assert len(quadkey) == 10
        assert all(c in "0123" for c in quadkey)

        # Test quadkey to tile conversion (round trip)
        tile_x2, tile_y2 = grid_level_10._quadkey_to_tile_xy(quadkey)
        assert tile_x == tile_x2
        assert tile_y == tile_y2

    def test_repr(self, grid_level_10):
        """Test string representation of grid."""
        repr_str = repr(grid_level_10)
        assert "QuadkeyGrid" in repr_str
        assert "level=10" in repr_str


class TestQuadkeyEdgeCases:
    """Test edge cases and error conditions."""

    def test_extreme_coordinates(self):
        """Test with extreme but valid coordinates."""
        grid = QuadkeyGrid(level=5)

        extreme_coords = [
            (85.05, 179.99),  # Near max lat/lon
            (-85.05, -179.99),  # Near min lat/lon
            (0.0, 0.0),  # Origin
        ]

        for lat, lon in extreme_coords:
            cell = grid.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert len(cell.identifier) == 5

    def test_coordinate_clamping(self):
        """Test that coordinates are properly clamped to valid ranges."""
        grid = QuadkeyGrid(level=5)

        # Test coordinates outside valid range (should be clamped)
        extreme_coords = [
            (90.0, 180.0),  # Exactly at poles/dateline
            (-90.0, -180.0),  # Exactly at poles/antimeridian
            (100.0, 200.0),  # Beyond valid range
            (-100.0, -200.0),  # Beyond valid range
        ]

        for lat, lon in extreme_coords:
            # Should not raise exception, coordinates should be clamped
            cell = grid.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)

    def test_empty_bbox(self):
        """Test with empty bounding box."""
        grid = QuadkeyGrid(level=10)

        # Point bounding box (min == max)
        cells = grid.get_cells_in_bbox(40.7, -74.0, 40.7, -74.0)

        # Should return at least one cell
        assert len(cells) >= 1

    def test_inverted_bbox(self):
        """Test with inverted bounding box coordinates."""
        grid = QuadkeyGrid(level=10)

        # Inverted bbox (min > max)
        cells = grid.get_cells_in_bbox(41.0, -73.0, 40.0, -74.0)

        # Should handle gracefully (might return empty or swap coordinates)
        assert isinstance(cells, list)


class TestQuadkeyProperties:
    """Test specific properties of Quadkey system."""

    def test_quadkey_length_equals_level(self):
        """Test that quadkey length always equals the level."""
        levels = [1, 5, 10, 15, 20, 23]
        lat, lon = 40.7128, -74.0060

        for level in levels:
            grid = QuadkeyGrid(level=level)
            cell = grid.get_cell_from_point(lat, lon)
            assert len(cell.identifier) == level

    def test_child_quadkey_prefix(self):
        """Test that child quadkeys start with parent quadkey."""
        grid = QuadkeyGrid(level=10)
        cell = grid.get_cell_from_point(40.7128, -74.0060)
        children = grid.get_children(cell)

        for child in children:
            assert child.identifier.startswith(cell.identifier)
            assert len(child.identifier) == len(cell.identifier) + 1

    def test_quadkey_digits_only_0123(self):
        """Test that quadkeys contain only digits 0, 1, 2, 3."""
        grid = QuadkeyGrid(level=10)

        # Test multiple points
        test_points = [
            (40.7128, -74.0060),
            (34.0522, -118.2437),
            (51.5074, -0.1278),
            (-33.8688, 151.2093),
        ]

        for lat, lon in test_points:
            cell = grid.get_cell_from_point(lat, lon)
            assert all(c in "0123" for c in cell.identifier)

    def test_spatial_locality(self):
        """Test that nearby points have similar quadkeys."""
        grid = QuadkeyGrid(level=10)

        # Two nearby points
        lat1, lon1 = 40.7128, -74.0060
        lat2, lon2 = 40.7130, -74.0062  # Very close to first point

        cell1 = grid.get_cell_from_point(lat1, lon1)
        cell2 = grid.get_cell_from_point(lat2, lon2)

        # Quadkeys should be the same or very similar
        # Count common prefix length
        common_prefix = 0
        for c1, c2 in zip(cell1.identifier, cell2.identifier):
            if c1 == c2:
                common_prefix += 1
            else:
                break

        # Should have significant common prefix for nearby points
        assert common_prefix >= 7  # Most of the quadkey should be the same
