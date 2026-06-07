"""
Tests for the A5 pentagonal grid implementation.

A5Grid is a thin adapter over the shared ``m3s_core`` A5 grid; these tests check
the BaseGrid contract and the adapter's coordinate-order / identifier handling
rather than re-testing the core's geometry.
"""

import m3s_core
import pytest
from shapely.geometry import Point, Polygon

from m3s import A5Grid, list_grid_systems
from m3s.a5 import MAX_PRECISION, MIN_PRECISION
from m3s.base import GridCell


class TestA5Init:
    """Initialization and precision/area mapping."""

    def test_init_default(self):
        """Default grid is precision 8 (~520 km^2 cells), matching the docs."""
        grid = A5Grid()
        assert grid.precision == 8
        assert grid.area_km2 == pytest.approx(519.0, rel=0.01)

    def test_precision_range(self):
        """MIN/MAX mirror the A5 spec (0..30)."""
        assert MIN_PRECISION == 0
        assert MAX_PRECISION == 30

    def test_init_invalid_precision(self):
        """Out-of-range precision raises ValueError."""
        with pytest.raises(ValueError, match="precision must be between 0 and 30"):
            A5Grid(precision=-1)
        with pytest.raises(ValueError, match="precision must be between 0 and 30"):
            A5Grid(precision=31)

    @pytest.mark.parametrize("precision", [0, 1, 5, 9, 20, 30])
    def test_area_km2_matches_core(self, precision):
        """Grid area is the core's authalic cell area (m^2) converted to km^2."""
        assert A5Grid(precision).area_km2 == m3s_core.a5_cell_area_m2(precision) / 1e6


class TestA5Cells:
    """Point lookup, identifiers and round-tripping."""

    def test_get_cell_from_point_inside(self):
        """The returned cell polygon contains the query point."""
        grid = A5Grid(precision=9)
        for lat, lon in [(40.7, -74.0), (0.0, 0.0), (-33.9, 151.2), (60.0, 10.0)]:
            cell = grid.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert cell.precision == 9
            assert cell.polygon.buffer(1e-9).contains(Point(lon, lat))

    def test_get_cell_from_point_invalid(self):
        """Out-of-range coordinates raise ValueError."""
        grid = A5Grid(precision=9)
        with pytest.raises(ValueError, match="Latitude"):
            grid.get_cell_from_point(95.0, 0.0)
        with pytest.raises(ValueError, match="Longitude"):
            grid.get_cell_from_point(0.0, 200.0)

    def test_identifier_roundtrip(self):
        """Round-trip point -> identifier -> cell reproduces the cell."""
        grid = A5Grid(precision=10)
        cell = grid.get_cell_from_point(48.85, 2.35)  # Paris
        again = grid.get_cell_from_identifier(cell.identifier)
        assert again.identifier == cell.identifier
        assert again.precision == cell.precision
        assert again.polygon.equals(cell.polygon)

    def test_identifier_format(self):
        """Identifiers are 16-char hex strings encoding the resolution."""
        cell = A5Grid(precision=9).get_cell_from_point(0.0, 0.0)
        assert len(cell.identifier) == 16
        assert set(cell.identifier) <= set("0123456789abcdef")
        # resolution is encoded in the id, not in a fixed-length prefix
        assert m3s_core.a5_resolution(cell.identifier) == 9

    def test_invalid_identifier(self):
        """A non-hex identifier raises ValueError."""
        grid = A5Grid(precision=9)
        with pytest.raises(ValueError, match="Invalid A5 identifier"):
            grid.get_cell_from_identifier("not-hex-zzz")

    def test_identifier_to_precision(self):
        """Precision is derivable straight from the identifier."""
        grid = A5Grid(precision=7)
        ident = grid.get_cell_from_point(0.0, 0.0).identifier
        assert grid.identifier_to_precision(ident) == 7
        assert grid.identifier_to_precision("not-hex-zzz") is None


class TestA5Hierarchy:
    """Pentagonal aperture-4 hierarchy (5 children below res 1, 4 above)."""

    def test_parent_child_roundtrip(self):
        """A cell is listed among its parent's children, one resolution up."""
        grid = A5Grid(precision=9)
        for lat, lon in [(48.85, 2.35), (35.0, 139.0), (-33.9, 151.2)]:
            cell = grid.get_cell_from_point(lat, lon)
            parent = grid.get_parent(cell)
            assert parent.precision == cell.precision - 1
            child_ids = {c.identifier for c in grid.get_children(parent)}
            assert cell.identifier in child_ids

    def test_children_count(self):
        """Above resolution 1 a cell has 4 children; res 0 cells have 5."""
        cell9 = A5Grid(precision=9).get_cell_from_point(48.85, 2.35)
        assert len(A5Grid(precision=9).get_children(cell9)) == 4
        cell0 = A5Grid(precision=0).get_cell_from_point(48.85, 2.35)
        assert len(A5Grid(precision=0).get_children(cell0)) == 5

    def test_children_finest_empty(self):
        """The finest level (30) has no children."""
        grid = A5Grid(precision=MAX_PRECISION)
        cell = grid.get_cell_from_point(0.0, 0.0)
        assert grid.get_children(cell) == []

    def test_parent_coarsest_raises(self):
        """The coarsest level (0) has no parent."""
        grid = A5Grid(precision=0)
        cell = grid.get_cell_from_point(0.0, 0.0)
        with pytest.raises(ValueError, match="no parent"):
            grid.get_parent(cell)


class TestA5EqualArea:
    """A5 is equal-area: cell ground area is independent of latitude."""

    def test_equal_area_across_latitudes(self):
        """A precision-9 cell measures the same area from the equator to 85N."""
        grid = A5Grid(precision=9)
        areas = [
            grid.get_cell_from_point(lat, 10.0).area_km2 for lat in (0, 30, 60, 85)
        ]
        for area in areas:
            assert area == pytest.approx(grid.area_km2, rel=0.05)
        assert max(areas) == pytest.approx(min(areas), rel=0.02)


class TestA5Neighbors:
    """Neighbour queries."""

    def test_neighbors_unique_exclude_self(self):
        """A cell has a handful of unique neighbours, excluding itself."""
        grid = A5Grid(precision=6)
        for lat, lon in [(48.85, 2.35), (0.0, 0.0), (80.0, 0.0)]:
            cell = grid.get_cell_from_point(lat, lon)
            neighbors = grid.get_neighbors(cell)
            ids = {n.identifier for n in neighbors}
            assert 0 < len(neighbors) <= 8
            assert len(ids) == len(neighbors)  # unique
            assert cell.identifier not in ids
            assert all(n.precision == cell.precision for n in neighbors)


class TestA5Bbox:
    """Bounding-box queries."""

    def test_get_cells_in_bbox(self):
        """All returned cells intersect the box, which is covered at its centre."""
        grid = A5Grid(precision=11)
        min_lat, min_lon, max_lat, max_lon = 48.84, 2.30, 48.94, 2.40
        cells = grid.get_cells_in_bbox(min_lat, min_lon, max_lat, max_lon)
        assert len(cells) > 0
        bbox = Polygon(
            [
                (min_lon, min_lat),
                (max_lon, min_lat),
                (max_lon, max_lat),
                (min_lon, max_lat),
            ]
        )
        assert all(c.polygon.buffer(1e-9).intersects(bbox) for c in cells)
        # the cell containing the box centre is part of the result
        centre = grid.get_cell_from_point(
            (min_lat + max_lat) / 2, (min_lon + max_lon) / 2
        )
        assert centre.identifier in {c.identifier for c in cells}

    def test_bbox_smaller_than_cell(self):
        """A box smaller than one cell still returns its covering cell."""
        grid = A5Grid(precision=4)  # very large cells
        cells = grid.get_cells_in_bbox(48.850, 2.350, 48.851, 2.351)
        assert len(cells) >= 1

    def test_wide_bbox_covers_interior(self):
        """A wide box covers its mid-latitude interior, not just the edges.

        ``polygon_to_cells`` reads the ring edges as geodesics, so without edge
        densification a continent-wide box's constant-latitude edges bow
        poleward and every central cell drops out (the reported A5 gap over
        Europe). A mid-latitude interior point (away from the box centre, which
        the corner/centre fallback would cover anyway) must be returned.
        """
        grid = A5Grid(precision=3)
        cells = grid.get_cells_in_bbox(28.0, -60.0, 63.0, 80.0)
        interior = grid.get_cell_from_point(50.0, 9.0)  # central Europe
        assert interior.identifier in {c.identifier for c in cells}


class TestA5Edges:
    """Edge cases and registration."""

    def test_poles_and_dateline(self):
        """Points at the poles and the dateline return valid cells."""
        grid = A5Grid(precision=5)
        for lat, lon in [(89.9, 179.9), (-89.9, -179.9), (0.0, 180.0), (90.0, 0.0)]:
            cell = grid.get_cell_from_point(lat, lon)
            assert isinstance(cell, GridCell)
            assert cell.polygon.area > 0

    def test_registered(self):
        """The grid is discoverable via list_grid_systems and m3s.grids."""
        import m3s

        assert "a5" in m3s.grids()
        assert "a5" in list_grid_systems()["system"].values

    def test_golden_path(self):
        """m3s.A5.from_geometry returns a single cell for a point."""
        import m3s

        cell = m3s.A5.from_geometry((2.35, 48.85), precision=10)  # (lon, lat)
        assert isinstance(cell, GridCell)
        assert cell.precision == 10
