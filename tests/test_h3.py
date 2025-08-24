"""
Tests for H3Grid implementation.
"""

import pytest
from shapely.geometry import Polygon

from m3s import H3Grid


class TestH3Grid:
    def test_grid_initialization(self):
        grid = H3Grid(resolution=7)
        assert grid.precision == 7

    def test_invalid_resolution(self):
        with pytest.raises(ValueError):
            H3Grid(resolution=-1)
        with pytest.raises(ValueError):
            H3Grid(resolution=16)

    def test_get_cell_from_point(self):
        grid = H3Grid(resolution=7)
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        assert cell is not None
        assert cell.precision == 7
        assert isinstance(cell.polygon, Polygon)
        assert len(cell.identifier) > 0

    def test_get_cell_from_identifier(self):
        grid = H3Grid(resolution=7)

        # Get a cell first to have a valid identifier
        test_cell = grid.get_cell_from_point(40.7128, -74.0060)

        # Now test getting cell from that identifier
        cell = grid.get_cell_from_identifier(test_cell.identifier)
        assert cell.identifier == test_cell.identifier
        assert cell.precision == 7
        assert isinstance(cell.polygon, Polygon)

    def test_polygon_intersection(self):
        grid = H3Grid(resolution=6)

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
        grid = H3Grid(resolution=7)
        cell = grid.get_cell_from_point(40.7128, -74.0060)
        neighbors = grid.get_neighbors(cell)

        # H3 hexagons should have 6 neighbors
        assert len(neighbors) == 6
        for neighbor in neighbors:
            assert neighbor.identifier != cell.identifier

    def test_get_cells_in_bbox(self):
        grid = H3Grid(resolution=8)
        min_lat, min_lon = 40.7, -74.1
        max_lat, max_lon = 40.8, -74.0

        cells = grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)

        assert len(cells) > 0
        for cell in cells:
            assert isinstance(cell.polygon, Polygon)

    def test_resolution_info(self):
        grid = H3Grid(resolution=7)
        info = grid.get_resolution_info()

        assert info["resolution"] == 7
        assert info["edge_length_km"] > 0
        assert info["hexagon_area_km2"] > 0
        assert info["children_per_parent"] == 7
        assert info["neighbors_per_cell"] == 6

    def test_edge_length_and_area(self):
        grid = H3Grid(resolution=7)

        edge_length = grid.get_edge_length_km()
        area = grid.get_hexagon_area_km2()

        assert edge_length > 0
        assert area > 0

        # Higher resolution should have smaller cells
        grid_higher = H3Grid(resolution=8)
        assert grid_higher.get_edge_length_km() < edge_length
        assert grid_higher.get_hexagon_area_km2() < area

    def test_parent_child_relationships(self):
        grid = H3Grid(resolution=7)
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        # Test getting children
        children = grid.get_children(cell)
        assert len(children) == 7  # H3 cells have 7 children

        for child in children:
            assert child.precision == 8  # One level higher resolution

        # Test getting parent
        parent = grid.get_parent(cell)
        assert parent.precision == 6  # One level lower resolution

    def test_compact_uncompact(self):
        grid = H3Grid(resolution=8)

        # Get some cells
        cells = grid.get_cells_in_bbox(40.7, -74.1, 40.75, -74.05)

        if len(cells) > 1:
            # Test compacting
            compacted = grid.compact_cells(cells)
            # Compacted should have same or fewer cells
            assert len(compacted) <= len(cells)

            # Test uncompacting back to original resolution
            uncompacted = grid.uncompact_cells(compacted, 8)
            # Should have at least as many cells as original
            assert len(uncompacted) >= len(compacted)

    def test_hexagon_properties(self):
        """Test that H3 cells are indeed hexagonal."""
        grid = H3Grid(resolution=7)
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        # H3 hexagons should have 6 vertices (plus closing vertex = 7 coordinates)
        exterior_coords = list(cell.polygon.exterior.coords)

        # Should have 7 coordinates (6 vertices + 1 closing)
        assert len(exterior_coords) == 7

        # First and last coordinates should be the same (closed polygon)
        assert exterior_coords[0] == exterior_coords[-1]
