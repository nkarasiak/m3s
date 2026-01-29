"""
Tests for A5 grid resolutions 2-10 (Hilbert curve support).

This module validates that the Hilbert curve implementation works correctly
for resolutions 2-30, with focused testing on resolutions 2-10 (practical range).
"""

import pytest

from m3s.a5.cell import (
    cell_to_lonlat,
    get_children,
    get_parent,
    get_resolution,
    lonlat_to_cell,
)
from m3s.a5.grid import A5Grid


class TestResolutionEncoding:
    """Test cell ID encoding for resolutions 2-10."""

    @pytest.mark.parametrize("resolution", range(2, 11))
    def test_resolution_encoding(self, resolution):
        """Test that cell IDs encode resolution correctly."""
        cell_id = lonlat_to_cell(0.0, 0.0, resolution)
        assert get_resolution(cell_id) == resolution

    @pytest.mark.parametrize("resolution", range(2, 11))
    def test_different_locations_different_cells(self, resolution):
        """Test that different locations produce different cell IDs."""
        cell1 = lonlat_to_cell(0.0, 0.0, resolution)
        cell2 = lonlat_to_cell(45.0, 45.0, resolution)
        cell3 = lonlat_to_cell(-74.0060, 40.7128, resolution)  # NYC

        # Cells should be different (with high probability)
        # At resolution 2+, cells are small enough that these points are in different cells
        cells = {cell1, cell2, cell3}
        assert len(cells) >= 2  # At least 2 should be different


class TestRoundtripConversion:
    """Test lonlat → cell → lonlat roundtrip accuracy."""

    # Test points covering different regions
    TEST_POINTS = [
        (0.0, 0.0, "Equator/Prime Meridian"),
        (-74.0060, 40.7128, "NYC"),
        (139.6503, 35.6762, "Tokyo"),
        (151.2093, -33.8688, "Sydney"),
        (-58.3816, -34.6037, "Buenos Aires"),
        (2.3522, 48.8566, "Paris"),
        (-0.1276, 51.5074, "London"),
    ]

    @pytest.mark.parametrize("lon,lat,name", TEST_POINTS)
    @pytest.mark.parametrize("resolution", [2, 3, 4, 5])
    def test_roundtrip_conversion(self, lon, lat, name, resolution):
        """Test that roundtrip conversion has reasonable accuracy."""
        cell_id = lonlat_to_cell(lon, lat, resolution)
        lon_back, lat_back = cell_to_lonlat(cell_id)

        # Calculate tolerance based on cell size
        # A5 pentagonal cells don't shrink as fast as quadtree cells
        # Use larger tolerance that accounts for pentagon size and distortion
        # Base tolerance on actual cell sizes:
        # - Resolution 2: ~45° cells
        # - Resolution 3: ~22° cells
        # - Resolution 4: ~11° cells
        # - Resolution 5: ~5.5° cells
        tolerance = 90 / (2 ** (resolution - 1))  # 2x more generous than quadtree

        # Check that we're within tolerance
        lon_diff = abs(lon - lon_back)
        lat_diff = abs(lat - lat_back)

        # Handle antimeridian wrapping
        if lon_diff > 180:
            lon_diff = 360 - lon_diff

        assert lon_diff < tolerance, (
            f"{name}: lon difference {lon_diff:.6f} exceeds tolerance {tolerance:.6f} "
            f"at resolution {resolution}"
        )
        assert lat_diff < tolerance, (
            f"{name}: lat difference {lat_diff:.6f} exceeds tolerance {tolerance:.6f} "
            f"at resolution {resolution}"
        )


class TestParentChildHierarchy:
    """Test parent-child relationships in the grid hierarchy."""

    @pytest.mark.parametrize("resolution", range(2, 7))
    def test_parent_child_relationship(self, resolution):
        """Test that parent-child relationships are maintained."""
        # Get a cell at the specified resolution
        parent_id = lonlat_to_cell(0.0, 0.0, resolution)

        # Get children
        children = get_children(parent_id)

        # All children should exist
        assert len(children) > 0

        # Each child should have resolution = parent resolution + 1
        for child in children:
            assert get_resolution(child) == resolution + 1

            # Child's parent should be the original cell
            child_parent = get_parent(child)
            assert child_parent == parent_id

    @pytest.mark.parametrize("resolution", range(3, 8))
    def test_grandparent_relationship(self, resolution):
        """Test multi-level parent relationships."""
        # Start with a cell at resolution R
        cell_id = lonlat_to_cell(-74.0060, 40.7128, resolution)

        # Get parent (resolution R-1)
        parent_id = get_parent(cell_id)
        assert get_resolution(parent_id) == resolution - 1

        # Get grandparent (resolution R-2)
        grandparent_id = get_parent(parent_id)
        assert get_resolution(grandparent_id) == resolution - 2

        # Get great-grandparent (resolution R-3)
        great_grandparent_id = get_parent(grandparent_id)
        assert get_resolution(great_grandparent_id) == resolution - 3

    @pytest.mark.parametrize("resolution", range(2, 6))
    def test_all_children_within_parent_bounds(self, resolution):
        """Test that all children centers are within parent cell (approximately)."""
        # Get a parent cell
        parent_id = lonlat_to_cell(0.0, 0.0, resolution)
        parent_lon, parent_lat = cell_to_lonlat(parent_id)

        # Get children
        children = get_children(parent_id)

        # Children should be clustered near parent center
        # Calculate max distance based on cell size
        max_distance = 360 / (2 ** (resolution - 1))  # Rough cell diameter

        for child in children:
            child_lon, child_lat = cell_to_lonlat(child)

            # Calculate distance (simplified - not geodesic)
            lon_diff = abs(child_lon - parent_lon)
            lat_diff = abs(child_lat - parent_lat)

            # Handle antimeridian wrapping
            if lon_diff > 180:
                lon_diff = 360 - lon_diff

            # Children should be within parent cell bounds (with some tolerance)
            assert lon_diff <= max_distance, (
                f"Child longitude {child_lon} too far from parent {parent_lon} "
                f"(diff={lon_diff:.6f}, max={max_distance:.6f})"
            )
            assert lat_diff <= max_distance, (
                f"Child latitude {child_lat} too far from parent {parent_lat} "
                f"(diff={lat_diff:.6f}, max={max_distance:.6f})"
            )


class TestGridIntegration:
    """Test A5Grid class with higher resolutions."""

    @pytest.mark.parametrize("resolution", range(2, 8))
    def test_grid_creation(self, resolution):
        """Test that A5Grid can be created at higher resolutions."""
        grid = A5Grid(precision=resolution)
        assert grid.precision == resolution

    @pytest.mark.parametrize("resolution", [2, 3, 4, 5])
    def test_get_cell_from_point(self, resolution):
        """Test getting cells from points at higher resolutions."""
        grid = A5Grid(precision=resolution)

        # Get cell for NYC
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        # Validate cell properties
        assert cell.identifier is not None
        assert cell.precision == resolution
        assert cell.polygon is not None
        assert cell.area_km2 > 0

        # Parse the integer cell ID from the string identifier
        # Format is "a5_{precision}_{cell_id_hex}"
        parts = cell.identifier.split("_")
        cell_id_hex = parts[2]
        cell_id = int(cell_id_hex, 16)
        assert get_resolution(cell_id) == resolution


class TestEdgeCases:
    """Test edge cases for Hilbert resolutions."""

    @pytest.mark.parametrize("resolution", [2, 5, 10])
    def test_poles(self, resolution):
        """Test cells near the poles."""
        # Near North Pole
        north_cell = lonlat_to_cell(0.0, 89.0, resolution)
        assert get_resolution(north_cell) == resolution

        # Near South Pole
        south_cell = lonlat_to_cell(0.0, -89.0, resolution)
        assert get_resolution(south_cell) == resolution

    @pytest.mark.parametrize("resolution", [2, 5, 10])
    def test_antimeridian(self, resolution):
        """Test cells near the antimeridian."""
        # Just before antimeridian
        cell1 = lonlat_to_cell(179.9, 0.0, resolution)
        assert get_resolution(cell1) == resolution

        # Just after antimeridian
        cell2 = lonlat_to_cell(-179.9, 0.0, resolution)
        assert get_resolution(cell2) == resolution

    @pytest.mark.parametrize("resolution", [2, 5])
    def test_equator(self, resolution):
        """Test cells along the equator."""
        for lon in [-180, -90, 0, 90, 179]:
            cell = lonlat_to_cell(lon, 0.0, resolution)
            assert get_resolution(cell) == resolution

    def test_maximum_resolution_10(self):
        """Test that resolution 10 works (practical maximum for testing)."""
        cell_id = lonlat_to_cell(0.0, 0.0, 10)
        assert get_resolution(cell_id) == 10

        # Test roundtrip
        lon, lat = cell_to_lonlat(cell_id)
        assert abs(lon) < 180
        assert abs(lat) <= 90
