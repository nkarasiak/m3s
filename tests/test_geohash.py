"""
Tests for GeohashGrid implementation.
"""

import pytest
from shapely.geometry import Polygon

from m3s import GeohashGrid


class TestGeohashGrid:
    """Test GeohashGrid behavior."""

    def test_grid_initialization(self):
        """Initialize grid with valid precision."""
        grid = GeohashGrid(precision=5)
        assert grid.precision == 5

    def test_invalid_precision(self):
        """Reject invalid precision values."""
        with pytest.raises(ValueError):
            GeohashGrid(precision=0)
        with pytest.raises(ValueError):
            GeohashGrid(precision=13)

    def test_get_cell_from_point(self):
        """Return a cell for a point."""
        grid = GeohashGrid(precision=5)
        cell = grid.get_cell_from_point(40.7128, -74.0060)

        assert cell is not None
        assert len(cell.identifier) == 5
        assert cell.precision == 5
        assert isinstance(cell.polygon, Polygon)

    def test_get_cell_from_identifier(self):
        """Return a cell for a geohash identifier."""
        grid = GeohashGrid(precision=5)
        cell = grid.get_cell_from_identifier("dr5ru")

        assert cell.identifier == "dr5ru"
        assert cell.precision == 5
        assert isinstance(cell.polygon, Polygon)

    def test_polygon_intersection(self):
        """Find cells intersecting a polygon."""
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
        """Return neighbor cells."""
        grid = GeohashGrid(precision=3)
        cell = grid.get_cell_from_point(40.7128, -74.0060)
        neighbors = grid.get_neighbors(cell)

        assert len(neighbors) > 0
        for neighbor in neighbors:
            assert neighbor.identifier != cell.identifier

    def test_expand_cell(self):
        """Expand a cell into subcells."""
        grid = GeohashGrid(precision=3)
        cell = grid.get_cell_from_identifier("dr5")
        expanded = grid.expand_cell(cell)

        assert len(expanded) == 32
        for expanded_cell in expanded:
            assert expanded_cell.identifier.startswith(cell.identifier)
            assert len(expanded_cell.identifier) == len(cell.identifier) + 1


class TestGeohashHierarchy:
    """Geohash exposes the standard get_children/get_parent interface."""

    def test_get_children(self):
        """A cell has 32 children one precision finer, each nested within it."""
        grid = GeohashGrid(precision=3)
        cell = grid.get_cell_from_identifier("dr5")
        children = grid.get_children(cell)

        assert len(children) == 32
        for child in children:
            assert child.identifier.startswith(cell.identifier)
            assert child.precision == cell.precision + 1
            assert cell.polygon.buffer(1e-9).contains(child.polygon.centroid)

    def test_get_children_finest_empty(self):
        """The finest precision (12) has no children."""
        grid = GeohashGrid(precision=12)
        cell = grid.get_cell_from_identifier("dr5regw3pg6t")
        assert grid.get_children(cell) == []

    def test_get_parent(self):
        """The parent drops the last character and is one precision coarser."""
        grid = GeohashGrid(precision=4)
        cell = grid.get_cell_from_identifier("dr5r")
        parent = grid.get_parent(cell)
        assert parent.identifier == "dr5"
        assert parent.precision == 3

    def test_get_parent_coarsest_raises(self):
        """The coarsest precision (1) has no parent."""
        grid = GeohashGrid(precision=1)
        cell = grid.get_cell_from_identifier("d")
        with pytest.raises(ValueError):
            grid.get_parent(cell)

    def test_refine_coarsen_roundtrip(self):
        """The wrapper's refine/coarsen work now that hierarchy is supported."""
        import m3s

        cell = m3s.Geohash.from_point(-74.0060, 40.7128, precision=5)
        collection = m3s.Geohash.neighbors(cell)
        refined = collection.refine(6)
        assert all(c.precision == 6 for c in refined)
        coarsened = collection.coarsen(4)
        assert all(c.precision == 4 for c in coarsened)
